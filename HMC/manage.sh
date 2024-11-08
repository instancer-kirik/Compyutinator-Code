#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
CONFIG_DIR="$HOME/.config/system_config"
BACKUP_DIR="$CONFIG_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Essential packages for different package managers
NIX_ESSENTIALS=(
    "git"
    "vim"
    "kmonad"
    "firefox"
    "alacritty"
)

FLATPAK_ESSENTIALS=(
    "com.spotify.Client"
    "org.signal.Signal"
)

# Configuration files to track
CONFIGS=(
    "$HOME/.config/kmonad/custom.kbd"
    "$HOME/.config/alacritty/alacritty.yml"
    "$HOME/.config/nvim/init.vim"
    "$HOME/.bashrc"
    "$HOME/.zshrc"
)

# Create required directories
mkdir -p "$CONFIG_DIR/"{configs,packages,scripts}
mkdir -p "$BACKUP_DIR"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to backup configurations
backup_configs() {
    echo -e "${BLUE}Backing up configurations...${NC}"
    
    # Create backup directory with timestamp
    local backup_path="$BACKUP_DIR/$TIMESTAMP"
    mkdir -p "$backup_path"

    # Backup each config file
    for config in "${CONFIGS[@]}"; do
        if [ -f "$config" ]; then
            # Preserve directory structure
            local rel_path=${config#$HOME/}
            local backup_file="$backup_path/$rel_path"
            mkdir -p "$(dirname "$backup_file")"
            cp "$config" "$backup_file"
            echo "Backed up: $config"
        fi
    done

    # Backup package lists
    mkdir -p "$backup_path/packages"
    
    if command_exists nix-env; then
        nix-env -q > "$backup_path/packages/nix-packages.txt"
    fi
    
    if command_exists flatpak; then
        flatpak list --app --columns=application > "$backup_path/packages/flatpak-packages.txt"
    fi

    echo -e "${GREEN}Backup completed: $backup_path${NC}"
}

# Function to restore configurations
restore_configs() {
    local backups=("$BACKUP_DIR"/*)
    if [ ${#backups[@]} -eq 0 ]; then
        echo -e "${RED}No backups found${NC}"
        return 1
    fi

    echo -e "${YELLOW}Available backups:${NC}"
    select backup in "${backups[@]}"; do
        if [ -n "$backup" ]; then
            echo -e "${BLUE}Restoring from: $backup${NC}"
            
            # Restore config files
            find "$backup" -type f -not -path "*/packages/*" | while read -r file; do
                local rel_path=${file#$backup/}
                local dest="$HOME/$rel_path"
                mkdir -p "$(dirname "$dest")"
                cp "$file" "$dest"
                echo "Restored: $dest"
            done
            
            echo -e "${GREEN}Configuration restored${NC}"
            break
        fi
    done
}

# Function to install essential packages
install_essentials() {
    echo -e "${BLUE}Installing essential packages...${NC}"

    # Nix packages
    if command_exists nix-env; then
        echo "Installing Nix packages..."
        for pkg in "${NIX_ESSENTIALS[@]}"; do
            nix-env -iA nixpkgs."$pkg" || echo "Failed to install: $pkg"
        done
    fi

    # Flatpak packages
    if command_exists flatpak; then
        echo "Installing Flatpak packages..."
        for pkg in "${FLATPAK_ESSENTIALS[@]}"; do
            flatpak install -y flathub "$pkg" || echo "Failed to install: $pkg"
        done
    fi
}

# Function to check system health
check_health() {
    echo -e "${BLUE}Checking system health...${NC}"

    # Check if essential services are running
    echo "Checking services..."
    if pgrep -x "kmonad" >/dev/null; then
        echo -e "${GREEN}KMonad is running${NC}"
    else
        echo -e "${RED}KMonad is not running${NC}"
    fi

    # Check disk space
    echo -e "\nDisk space usage:"
    df -h /home

    # Check memory usage
    echo -e "\nMemory usage:"
    free -h

    # Check for common configuration issues
    echo -e "\nChecking configurations..."
    for config in "${CONFIGS[@]}"; do
        if [ -f "$config" ]; then
            echo -e "${GREEN}Found: $config${NC}"
        else
            echo -e "${RED}Missing: $config${NC}"
        fi
    done
}

# Function to sync configurations
sync_configs() {
    echo -e "${BLUE}Syncing configurations...${NC}"
    
    # Create a git repository if it doesn't exist
    if [ ! -d "$CONFIG_DIR/.git" ]; then
        git init "$CONFIG_DIR"
    fi

    # Copy current configs
    for config in "${CONFIGS[@]}"; do
        if [ -f "$config" ]; then
            local rel_path=${config#$HOME/}
            local dest="$CONFIG_DIR/configs/$rel_path"
            mkdir -p "$(dirname "$dest")"
            cp "$config" "$dest"
            echo "Synced: $config"
        fi
    done

    # Commit changes
    cd "$CONFIG_DIR" || exit
    git add .
    git commit -m "Config sync: $TIMESTAMP"
}

# Main menu
show_menu() {
    echo -e "\n${YELLOW}=== System Configuration Manager ===${NC}"
    echo "1. Backup configurations"
    echo "2. Restore configurations"
    echo "3. Install essential packages"
    echo "4. Check system health"
    echo "5. Sync configurations"
    echo "6. Exit"
    echo -n "Select an option: "
}

# Main loop
while true; do
    show_menu
    read -r option

    case $option in
        1) backup_configs ;;
        2) restore_configs ;;
        3) install_essentials ;;
        4) check_health ;;
        5) sync_configs ;;
        6) 
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac

    echo -e "\nPress Enter to continue..."
    read -r
done 