import time, math, os, sys
import logging
import numpy as np
import json
import logging
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult
from skysolve_next.solver.tetra3_solver import Tetra3Solver
from skysolve_next.solver.astrometry_solver import AstrometrySolver
from skysolve_next.publish.lx200_server import LX200Server
from skysolve_next.mounts.onstep.lx200 import OnStepClient


# Ensure all logs go to stdout for VS Code Debug Console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout
)


import sys
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError as e:
    print(f"[DIAG] picamera2 import failed: {e}")
    PICAMERA2_AVAILABLE = False

print(f"[DIAG] PICAMERA2_AVAILABLE: {PICAMERA2_AVAILABLE}")
print(f"[DIAG] sys.platform: {sys.platform}")

PREVIEW_PATH = "skysolve_next/web/solve/last_image.jpg"
STATUS_PATH = "skysolve_next/web/worker_status.json"

class CameraCapture:
    def __init__(self, settings):
        self.settings = settings
        self.latest_frame = None
        self.last_error = None
        self.picam = None
        self.is_pi = PICAMERA2_AVAILABLE and sys.platform.startswith("linux")
        self.logger = logging.getLogger("skysolve.camera")
        self.logger.info(f"[DIAG] CameraCapture init: is_pi={self.is_pi}, PICAMERA2_AVAILABLE={PICAMERA2_AVAILABLE}, sys.platform={sys.platform}")
        if not self.logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(h)
        self.logger.setLevel(logging.DEBUG)
        if self.is_pi:
            try:
                from picamera2 import Picamera2
                self.picam = Picamera2()
                cam_settings = self.settings.camera
                size = tuple(map(int, cam_settings.image_size.split("x")))
                config = self.picam.create_still_configuration(main={"size": size, "format": "RGB888"})
                self.picam.configure(config)
                self.picam.set_controls({
                    "ExposureTime": int(float(cam_settings.shutter_speed) * 1e6),
                    "AnalogueGain": float(cam_settings.iso_speed) / 100.0,
                    "AeEnable": False
                })
                try:
                    self.picam.exposure_mode = 'off'
                except Exception as e:
                    self.logger.warning(f"exposure_mode could not be set: {e}")
                self.picam.start()
                self.logger.info("Picamera2 initialized and started successfully.")
            except Exception as e:
                self.last_error = f"Picamera2 init failed: {e}"
                self.is_pi = False
                self.logger.error(f"[DIAG] {self.last_error}")

    def configure_camera(self):
        # No longer used; configuration is done once in __init__
        pass

    def _parse_shutter(self, shutter_val):
        """Parse shutter speed from float or fraction string."""
        try:
            if isinstance(shutter_val, (int, float)):
                return float(shutter_val)
            s = str(shutter_val).strip()
            if '/' in s:
                num, denom = s.split('/')
                return float(num) / float(denom)
            return float(s)
        except Exception as e:
            self.logger.warning(f"Could not parse shutter speed '{shutter_val}': {e}, defaulting to 1.0s")
            return 1.0

    def capture(self):
        self.logger.debug("Starting image capture...")
        if self.is_pi and self.picam:
            try:
                # Reload camera settings before each capture
                self.settings.reload_if_changed()
                cam_settings = self.settings.camera
                # Parse shutter and ISO
                shutter_val = getattr(cam_settings, "shutter_speed", 1)
                shutter = self._parse_shutter(shutter_val)
                iso_val = getattr(cam_settings, "iso_speed", 100)
                # Update controls if changed
                controls = {
                    "ExposureTime": int(shutter * 1e6),
                    "AnalogueGain": float(iso_val) / 100.0,
                    "AeEnable": False
                }
                self.picam.set_controls(controls)
                self.logger.debug(f"Set camera controls: {controls}")
                frame = self.picam.capture_array()
                self.save_preview(frame)
                self.latest_frame = frame
                self.last_error = None
                self.logger.info("Image captured successfully.")
                # Sleep for shutter speed to simulate exposure time
                try:
                    self.logger.debug(f"Sleeping for shutter speed: {shutter}s")
                    time.sleep(max(0.01, shutter))
                except Exception as sleep_e:
                    self.logger.warning(f"Could not sleep for shutter: {sleep_e}")
                return frame
            except Exception as e:
                self.last_error = f"Camera capture failed: {e}"
                self.logger.error(self.last_error)
                frame = np.zeros((256,256), dtype=np.uint8)
                self.latest_frame = frame
                return frame
        else:
            # Use demo image for mock frame
            try:
                import cv2
                frame = cv2.imread("skysolve_next/web/static/demo.jpg", cv2.IMREAD_GRAYSCALE)
                if frame is None:
                    raise Exception("Demo image not found or unreadable")
                # Simulate shutter speed delay
                shutter = float(getattr(self.settings.camera, "shutter_speed", "1"))
                time.sleep(max(0.01, shutter))
                self.save_preview(frame)
                self.latest_frame = frame
                self.logger.info("Demo image loaded successfully.")
            except Exception as e:
                self.last_error = f"Demo image load failed: {e}"
                self.logger.error(self.last_error)
                frame = np.zeros((256,256), dtype=np.uint8)
                self.latest_frame = frame
            return frame

    def save_preview(self, frame):
        try:
            import cv2
            import shutil
            cv2.imwrite(PREVIEW_PATH, frame)
            self.logger.debug(f"Preview image saved to {PREVIEW_PATH}")
            # Also copy to image.jpg for UI preview
            IMAGE_PATH = "skysolve_next/web/solve/image.jpg"
            try:
                shutil.copyfile(PREVIEW_PATH, IMAGE_PATH)
                self.logger.debug(f"Preview image copied to {IMAGE_PATH}")
            except Exception as copy_e:
                self.logger.error(f"Failed to copy preview to {IMAGE_PATH}: {copy_e}")
        except Exception as e:
            self.last_error = f"Preview save failed: {e}"
            self.logger.error(self.last_error)
            # Fallback: save as raw bytes
            try:
                with open(PREVIEW_PATH, "wb") as f:
                    f.write(frame.tobytes())
                self.logger.debug(f"Preview image saved as raw bytes to {PREVIEW_PATH}")
                # Also try to copy as raw bytes
                IMAGE_PATH = "skysolve_next/web/solve/image.jpg"
                try:
                    shutil.copyfile(PREVIEW_PATH, IMAGE_PATH)
                    self.logger.debug(f"Raw preview image copied to {IMAGE_PATH}")
                except Exception as copy_e:
                    self.logger.error(f"Failed to copy raw preview to {IMAGE_PATH}: {copy_e}")
            except Exception as e2:
                self.last_error = f"Preview save failed: {e}; fallback failed: {e2}"
                self.logger.error(self.last_error)

    def get_latest_frame(self):
        return self.latest_frame

    def get_last_error(self):
        return self.last_error

def write_status(mode, res, error=None):
    import os
    # Load previous status if exists
    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, "r") as f:
            prev = json.load(f)
    else:
        prev = {}
    ra = getattr(res, 'ra_deg', None)
    dec = getattr(res, 'dec_deg', None)
    conf = getattr(res, 'confidence', None)
    # Only update timestamp and RA/Dec if mode is 'solve' and RA/Dec are not None
    if mode == "solve" and ra is not None and dec is not None:
        status = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
            "mode": mode,
            "ra": ra,
            "dec": dec,
            "confidence": conf if conf not in (None, 0.0) else "-",
            "error": error
        }
    else:
        # Keep previous values for timestamp, ra, dec, confidence
        status = {
            "timestamp": prev.get("timestamp"),
            "mode": mode,
            "ra": prev.get("ra"),
            "dec": prev.get("dec"),
            "confidence": prev.get("confidence"),
            "error": error
        }
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f)


    pass  # Removed for single-threaded mode

def main():
    logger = logging.getLogger("skysolve.main")
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(h)
    logger.setLevel(logging.DEBUG)

    logger.info(f"Starting LX200 server on port {settings.lx200_port}")
    lx200 = LX200Server(port=settings.lx200_port)
    lx200.start()

    onstep = OnStepClient() if settings.onstep.enabled else None
    if onstep:
        logger.info("OnStep client enabled.")

    logger.info(f"Mode: {settings.mode}")

    camera = CameraCapture(settings)
    last_ra = None
    last_dec = None
    last_mode = settings.mode
    while True:
        logger.info("[DIAG] Top of main loop")
        try:
            settings.reload_if_changed()
            mode = settings.mode.lower()
            error = None
            res = SolveResult(ra_deg=None, dec_deg=None, roll_deg=None, plate_scale_arcsec_px=None, confidence=None)
            if mode != last_mode:
                logger.info(f"Mode changed: {last_mode} -> {mode}")
                last_mode = mode
            if mode == "test":
                logger.info("[DIAG] In test mode loop")
                write_status(mode, res, error)
                logger.info("[DIAG] End of main loop (test mode)")
                time.sleep(1.0)
                continue
            elif mode == "align":
                logger.info("Align mode: capturing preview frame.")
                frame = camera.capture()
                logger.info("[DIAG] Finished camera.capture() in align mode")
                res = SolveResult(ra_deg=None, dec_deg=None, roll_deg=None, plate_scale_arcsec_px=None, confidence=None)
            else:
                logger.info("Solve mode: capturing frame and running solver.")
                frame = camera.capture()
                try:
                    if settings.solver.type == "tetra3":
                        primary = Tetra3Solver()
                        fallback = AstrometrySolver()
                    else:
                        primary = AstrometrySolver()
                        fallback = Tetra3Solver()
                    logger.info("Running primary solver...")
                    input_data = PREVIEW_PATH
                    if last_ra is not None and last_dec is not None:
                        res = primary.solve(input_data, ra_hint=last_ra, dec_hint=last_dec, radius_hint=settings.solver.solve_radius)
                    else:
                        res = primary.solve(input_data)
                    logger.info(f"Primary solver result: confidence={getattr(res, 'confidence', None)}")
                    conf = res.confidence
                    try:
                        conf_val = float(conf)
                    except (TypeError, ValueError):
                        conf_val = 1.0
                    # TODO: fallback logic can be restored here if needed
                except Exception as e:
                    error = f"Solver error: {e}"
                    camera.last_error = error
                    logger.error(error)
                if res and conf_val > 0.5:
                    last_ra = res.ra_deg
                    last_dec = res.dec_deg
                    logger.info(f"Updated last RA/Dec: RA={last_ra}, Dec={last_dec}")
            write_status(mode, res, error or camera.get_last_error())
            if lx200:
                lx200.publish(res)
            if onstep:
                try:
                    if settings.onstep_sync_mode == "slew_then_sync":
                        onstep.slew_then_sync(res)
                    else:
                        onstep.sync_pointing(res)
                except Exception as e:
                    logger.error(f"OnStep sync error: {e}")
            logger.info("[DIAG] End of main loop")
            time.sleep(0.1)
            logger.info("[DIAG] Slept 0.1s, about to next loop")
        except Exception as loop_exc:
            logger.error(f"[UNHANDLED EXCEPTION in main loop]: {loop_exc}", exc_info=True)
            time.sleep(1.0)

    pass  # Removed for single-threaded mode

    logger = logging.getLogger("skysolve.main")
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(h)
    logger.setLevel(logging.DEBUG)

    logger.info(f"Starting LX200 server on port {settings.lx200_port}")
    lx200 = LX200Server(port=settings.lx200_port)
    lx200.start()

    onstep = OnStepClient() if settings.onstep.enabled else None
    if onstep:
        logger.info("OnStep client enabled.")

    logger.info(f"Mode: {settings.mode}")

    camera = CameraCapture(settings)
    last_ra = None
    last_dec = None
    last_mode = settings.mode
    while True:
        settings.reload_if_changed()
        mode = settings.mode.lower()
        error = None
        res = SolveResult(ra_deg=None, dec_deg=None, roll_deg=None, plate_scale_arcsec_px=None, confidence=None)
        if mode != last_mode:
            logger.info(f"Mode changed: {last_mode} -> {mode}")
            last_mode = mode
        if mode == "test":
            write_status(mode, res, error)
            time.sleep(1.5)
            continue
        elif mode == "align":
            logger.info("Align mode: capturing preview frame.")
            frame = camera.capture()
            res = SolveResult(ra_deg=None, dec_deg=None, roll_deg=None, plate_scale_arcsec_px=None, confidence=None)
        else:
            logger.info("Solve mode: capturing frame and running solver.")
            frame = camera.capture()
            try:
                if settings.solver.type == "tetra3":
                    primary = Tetra3Solver()
                    fallback = AstrometrySolver()
                else:
                    primary = AstrometrySolver()
                    fallback = Tetra3Solver()
                logger.info("Running primary solver...")
                input_data = PREVIEW_PATH
                if last_ra is not None and last_dec is not None:
                    res = primary.solve(input_data, ra_hint=last_ra, dec_hint=last_dec, radius_hint=settings.solver.solve_radius)
                else:
                    res = primary.solve(input_data)
                logger.info(f"Primary solver result: confidence={getattr(res, 'confidence', None)}")
                conf = res.confidence
                try:
                    conf_val = float(conf)
                except (TypeError, ValueError):
                    conf_val = 1.0
                # TODO: fallback logic can be restored here if needed
            except Exception as e:
                error = f"Solver error: {e}"
                camera.last_error = error
                logger.error(error)
            if res and conf_val > 0.5:
                last_ra = res.ra_deg
                last_dec = res.dec_deg
                logger.info(f"Updated last RA/Dec: RA={last_ra}, Dec={last_dec}")
        write_status(mode, res, error or camera.get_last_error())
        if lx200:
            lx200.publish(res)
        if onstep:
            try:
                if settings.onstep_sync_mode == "slew_then_sync":
                    onstep.slew_then_sync(res)
                else:
                    onstep.sync_pointing(res)
            except Exception as e:
                logger.error(f"OnStep sync error: {e}")
        time.sleep(1.5)

if __name__ == "__main__":
    main()
