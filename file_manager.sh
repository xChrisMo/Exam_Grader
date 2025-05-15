#!/bin/bash

# File Manager Script for Exam Grader
# This script allows adding and deleting files from the command line

# Display help information
show_help() {
    echo "File Manager for Exam Grader"
    echo "Usage:"
    echo "  ./file_manager.sh add <file_path> <destination_directory> - Add a file to the specified directory"
    echo "  ./file_manager.sh delete <file_path> - Delete a file"
    echo "  ./file_manager.sh list <directory> - List files in a directory"
    echo "  ./file_manager.sh help - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./file_manager.sh add ./my_file.txt ./data/submissions - Add my_file.txt to submissions directory"
    echo "  ./file_manager.sh delete ./data/submissions/my_file.txt - Delete a file"
    echo "  ./file_manager.sh list ./data/submissions - List all files in submissions directory"
}

# Function to add a file
add_file() {
    local source_file="$1"
    local destination_dir="$2"
    
    # Check if source file exists
    if [ ! -f "$source_file" ]; then
        echo "Error: Source file '$source_file' does not exist."
        exit 1
    fi
    
    # Check if destination directory exists, create if not
    if [ ! -d "$destination_dir" ]; then
        echo "Destination directory '$destination_dir' does not exist. Creating it..."
        mkdir -p "$destination_dir"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create destination directory."
            exit 1
        fi
    fi
    
    # Get the filename from the source path
    filename=$(basename "$source_file")
    
    # Copy the file to the destination
    cp "$source_file" "$destination_dir/$filename"
    
    if [ $? -eq 0 ]; then
        echo "File '$filename' successfully added to '$destination_dir'."
    else
        echo "Error: Failed to add file."
        exit 1
    fi
}

# Function to delete a file
delete_file() {
    local file_path="$1"
    
    # Check if file exists
    if [ ! -f "$file_path" ]; then
        echo "Error: File '$file_path' does not exist."
        exit 1
    fi
    
    # Confirm deletion
    read -p "Are you sure you want to delete '$file_path'? (y/n): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        rm "$file_path"
        if [ $? -eq 0 ]; then
            echo "File '$file_path' successfully deleted."
        else
            echo "Error: Failed to delete file."
            exit 1
        fi
    else
        echo "Deletion cancelled."
    fi
}

# Function to list files in a directory
list_files() {
    local directory="$1"
    
    # Check if directory exists
    if [ ! -d "$directory" ]; then
        echo "Error: Directory '$directory' does not exist."
        exit 1
    fi
    
    # Count files
    file_count=$(find "$directory" -type f | wc -l)
    
    echo "Files in '$directory' ($file_count files):"
    echo "----------------------------------------"
    
    # List files with details
    find "$directory" -type f -exec ls -lh {} \; | awk '{print $9, "(" $5 ")"}'
}

# Main script logic
case "$1" in
    add)
        if [ $# -ne 3 ]; then
            echo "Error: 'add' command requires a source file and destination directory."
            echo "Usage: ./file_manager.sh add <file_path> <destination_directory>"
            exit 1
        fi
        add_file "$2" "$3"
        ;;
    delete)
        if [ $# -ne 2 ]; then
            echo "Error: 'delete' command requires a file path."
            echo "Usage: ./file_manager.sh delete <file_path>"
            exit 1
        fi
        delete_file "$2"
        ;;
    list)
        if [ $# -ne 2 ]; then
            echo "Error: 'list' command requires a directory path."
            echo "Usage: ./file_manager.sh list <directory>"
            exit 1
        fi
        list_files "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Error: Unknown command '$1'"
        show_help
        exit 1
        ;;
esac

exit 0
