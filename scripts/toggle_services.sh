#!/bin/bash

# Script to toggle between legacy and next skysolve services
# Usage: ./toggle_services.sh [legacy|next|new]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service exists
service_exists() {
    systemctl list-unit-files | grep -q "^$1.service"
}

# Function to check if a service is active
service_active() {
    systemctl is-active --quiet "$1" 2>/dev/null
}

# Function to stop services if they exist and are running
stop_services() {
    local service_list=("$@")
    for service in "${service_list[@]}"; do
        if service_exists "$service"; then
            if service_active "$service"; then
                print_status "Stopping $service..."
                sudo systemctl stop "$service"
                print_success "Stopped $service"
            else
                print_status "$service is not running"
            fi
        else
            print_warning "Service $service does not exist"
        fi
    done
}

# Function to start services if they exist
start_services() {
    local service_list=("$@")
    for service in "${service_list[@]}"; do
        if service_exists "$service"; then
            print_status "Starting $service..."
            sudo systemctl start "$service"
            print_success "Started $service"
        else
            print_error "Service $service does not exist - cannot start"
            return 1
        fi
    done
}

# Function to show service status
show_status() {
    local service_list=("$@")
    echo ""
    print_status "Service Status:"
    for service in "${service_list[@]}"; do
        if service_exists "$service"; then
            if service_active "$service"; then
                echo -e "  ${GREEN}●${NC} $service (active)"
            else
                echo -e "  ${RED}○${NC} $service (inactive)"
            fi
        else
            echo -e "  ${YELLOW}?${NC} $service (not installed)"
        fi
    done
    echo ""
}

# Define service arrays
LEGACY_SERVICES=("skysolve" "encodertoSkySafari")
NEXT_SERVICES=("skysolve-web" "skysolve-worker")
ALL_SERVICES=("${LEGACY_SERVICES[@]}" "${NEXT_SERVICES[@]}")

# Parse command line argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 [legacy|next|new|status]"
    echo ""
    echo "Commands:"
    echo "  legacy  - Switch to legacy services (skysolve, encodertoSkySafari)"
    echo "  next    - Switch to next services (skysolve-web, skysolve-worker)"
    echo "  new     - Alias for 'next'"
    echo "  status  - Show current status of all services"
    echo ""
    show_status "${ALL_SERVICES[@]}"
    exit 1
fi

COMMAND="$1"

case "$COMMAND" in
    "legacy")
        print_status "Switching to legacy services..."
        
        # Stop next services
        print_status "Stopping next services..."
        stop_services "${NEXT_SERVICES[@]}"
        
        # Start legacy services
        print_status "Starting legacy services..."
        start_services "${LEGACY_SERVICES[@]}"
        
        print_success "Switched to legacy services"
        show_status "${ALL_SERVICES[@]}"
        ;;
        
    "next"|"new")
        print_status "Switching to next services..."
        
        # Stop legacy services
        print_status "Stopping legacy services..."
        stop_services "${LEGACY_SERVICES[@]}"
        
        # Start next services
        print_status "Starting next services..."
        start_services "${NEXT_SERVICES[@]}"
        
        print_success "Switched to next services"
        show_status "${ALL_SERVICES[@]}"
        ;;
        
    "status")
        show_status "${ALL_SERVICES[@]}"
        ;;
        
    *)
        print_error "Invalid command: $COMMAND"
        echo "Valid commands: legacy, next, new, status"
        exit 1
        ;;
esac
