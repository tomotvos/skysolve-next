import re
import pytest

SAMPLE_LOG = '''
[10:42:01] solve-field command: solve-field skysolve_next/web/static/last_image.jpg --overwrite --no-plots
[10:42:02] Reading input file 1 of 1: "skysolve_next/web/static/last_image.jpg"...
[10:42:02] Running command: /usr/local/bin/image2pnm --infile skysolve_next/web/static/last_image.jpg --uncompressed-outfile /tmp/tmp.uncompressed.TnDf2t --outfile /tmp/tmp.ppm.Q897Es --ppm --mydir /usr/local/bin/solve-field
[10:42:02] Extracting sources...
[10:42:02] simplexy: found 889 sources.
[10:42:02] Solving...
[10:42:02] Reading file "skysolve_next/web/static/last_image.axy"...
[10:42:02] log-odds ratio 152.937 (2.62717e+66), 46 match, 0 conflict, 87 distractors, 60 index.
[10:42:02] RA,Dec = (296.964,42.7365), pixel scale 80.7537 arcsec/pix.
[10:42:02] Hit/miss: Hit/miss: ++-+--+++++-++++--+++++-++++--++-++---+++-+--++-----+-+-+----+--+----------++---+-------+-+-+---+--+
[10:42:02] Field 1: solved with index index-4116.fits.
[10:42:02] Field 1 solved: writing to file skysolve_next/web/static/last_image.solved to indicate this.
[10:42:02] Field: skysolve_next/web/static/last_image.jpg
[10:42:02] Field center: (RA,Dec) = (296.944646, 42.688983) deg.
[10:42:02] Field center: (RA H:M:S, Dec D:M:S) = (19:47:46.715, +42:41:20.339).
[10:42:02] Field size: 22.849 x 17.2545 degrees
[10:42:02] Field rotation angle: up is -165.998 degrees E of N
[10:42:02] Field parity: neg
[10:42:02] Creating new FITS file "skysolve_next/web/static/last_image.new"...
[10:42:02]
[10:42:02] jpegtopnm: WRITING PPM FILE
[10:42:02] Read file stdin: 1024 x 768 pixels x 1 color(s); maxval 255
[10:42:02] Using 8-bit output
[10:42:02] Demo image solved. Total solve time: 0.99 seconds.
'''

def parse_ra_dec(log_lines):
    ra_deg = dec_deg = None
    for line in log_lines:
        # Remove timestamp prefix if present
        line_no_ts = re.sub(r"^\[\d{2}:\d{2}:\d{2}\]\s*", "", line)
        m1 = re.search(r"RA,Dec\s*=\s*\(([-\d.]+),\s*([-\d.]+)\)", line_no_ts)
        m2 = re.search(r"Field center: \(RA,Dec\) = \(([-\d.]+),\s*([-\d.]+)\)", line_no_ts)
        if m1:
            ra_deg = float(m1.group(1))
            dec_deg = float(m1.group(2))
        elif m2:
            ra_deg = float(m2.group(1))
            dec_deg = float(m2.group(2))
    return ra_deg, dec_deg

def test_parse_ra_dec():
    log_lines = SAMPLE_LOG.splitlines()
    ra, dec = parse_ra_dec(log_lines)
    assert ra == 296.964 or ra == 296.944646
    assert dec == 42.7365 or dec == 42.688983
