#!/bin/bash
#
# Twingate Manager - Installation Script
# Supports: Arch Linux, Debian, Ubuntu, Fedora
# Requires: KDE Plasma desktop environment
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run this script with sudo or as root."
        exit 1
    fi
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif [ -f /etc/arch-release ]; then
        DISTRO="arch"
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/fedora-release ]; then
        DISTRO="fedora"
    else
        log_error "Unsupported distribution."
        exit 1
    fi
    log_info "Detected distribution: $DISTRO"
}

install_dependencies() {
    log_info "Installing dependencies..."
    
    case $DISTRO in
        arch|cachyos|endeavouros|manjaro)
            pacman -Sy --noconfirm --needed python python-pyqt6
            ;;
        debian|ubuntu|linuxmint|pop)
            apt-get update
            apt-get install -y python3 python3-pyqt6
            ;;
        fedora|rhel|centos)
            dnf install -y python3 python3-qt6
            ;;
        opensuse*|suse)
            zypper install -y python3 python3-qt6
            ;;
        *)
            log_warn "Unknown distro, attempting pip install..."
            pip3 install PyQt6 || pip install PyQt6
            ;;
    esac
    
    log_info "Dependencies installed."
}

check_twingate() {
    if ! command -v twingate &> /dev/null; then
        log_warn "Twingate is not installed."
        log_info "Please install Twingate from: https://www.twingate.com/download"
        
        case $DISTRO in
            arch|cachyos|endeavouros|manjaro)
                log_info "For Arch-based: yay -S twingate"
                ;;
            debian|ubuntu|linuxmint|pop)
                log_info "For Debian/Ubuntu: Follow official Twingate docs"
                ;;
            fedora|rhel|centos)
                log_info "For Fedora: Follow official Twingate docs"
                ;;
        esac
        
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "Twingate found: $(twingate --version | head -1)"
    fi
}

create_directories() {
    log_info "Creating directories..."
    
    mkdir -p /etc/twingate/keys
    chmod 755 /etc/twingate
    chmod 755 /etc/twingate/keys
    
    log_info "Directories created."
}

install_files() {
    log_info "Installing application files..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    INSTALL_DIR="/opt/twingate-manager"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/icons"
    
    cp "$SCRIPT_DIR/twingate-tray.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/icons/"*.png "$INSTALL_DIR/icons/" 2>/dev/null || true
    
    cp "$SCRIPT_DIR/tg-switch" /usr/local/bin/
    chmod +x /usr/local/bin/tg-switch
    chmod +x "$INSTALL_DIR/twingate-tray.py"
    
    log_info "Application files installed to $INSTALL_DIR"
}

setup_sudoers() {
    log_info "Configuring passwordless sudo for tg-switch..."
    
    SUDOERS_FILE="/etc/sudoers.d/twingate-manager"
    
    cat > "$SUDOERS_FILE" << 'EOF'
# Twingate Manager - Allow users in wheel/sudo group to run tg-switch without password
%wheel ALL=(root) NOPASSWD: /usr/local/bin/tg-switch
%sudo ALL=(root) NOPASSWD: /usr/local/bin/tg-switch
EOF
    
    chmod 440 "$SUDOERS_FILE"
    
    log_info "Sudoers configured."
}

create_desktop_entry() {
    log_info "Creating desktop entry..."
    
    cat > /usr/share/applications/twingate-manager.desktop << EOF
[Desktop Entry]
Name=Twingate Manager
Comment=Manage Twingate VPN profiles
Exec=python3 /opt/twingate-manager/twingate-tray.py
Icon=/opt/twingate-manager/icons/twingate_on.png
Type=Application
Categories=Network;VPN;
Keywords=twingate;vpn;network;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF
    
    log_info "Desktop entry created."
}

create_autostart() {
    log_info "Creating autostart entry..."
    
    AUTOSTART_DIR="/etc/xdg/autostart"
    mkdir -p "$AUTOSTART_DIR"
    
    cat > "$AUTOSTART_DIR/twingate-manager.desktop" << EOF
[Desktop Entry]
Name=Twingate Manager
Comment=Manage Twingate VPN profiles
Exec=python3 /opt/twingate-manager/twingate-tray.py
Icon=/opt/twingate-manager/icons/twingate_on.png
Type=Application
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
EOF
    
    log_info "Autostart configured."
}

print_summary() {
    echo
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Twingate Manager installed successfully!  ${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo
    echo "Installation directory: /opt/twingate-manager"
    echo "Backend script: /usr/local/bin/tg-switch"
    echo "Profile keys: /etc/twingate/keys/"
    echo
    echo "To start now:"
    echo "  python3 /opt/twingate-manager/twingate-tray.py &"
    echo
    echo "The app will auto-start on next login."
    echo
}

main() {
    echo
    echo "Twingate Manager - Installation"
    echo "================================"
    echo
    
    check_root
    detect_distro
    install_dependencies
    check_twingate
    create_directories
    install_files
    setup_sudoers
    create_desktop_entry
    create_autostart
    print_summary
}

main "$@"
