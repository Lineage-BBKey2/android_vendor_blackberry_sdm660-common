FOLDER="/data4/LOS22/vendor/blackberry/sdm660-common/proprietary/vendor/lib64/"

if [[ -z "$FOLDER" ]]; then
    echo "Usage: $0 /path/to/folder"
    exit 1
fi

if ! command -v patchelf &> /dev/null; then
    echo "patchelf is not installed. Install it first."
    exit 1
fi

# Loop through all .so files
find "$FOLDER" -type f -name "*.so" | while read -r file; do
    filename=$(basename "$file")
    current_soname=$(patchelf --print-soname "$file" 2>/dev/null)
    
    if [[ "$current_soname" != "$filename" ]]; then
        echo "Updating SONAME for $file:"
        echo "  Current SONAME: $current_soname"
        echo "  New SONAME:     $filename"
        patchelf --set-soname "$filename" "$file"
    else
        echo "SONAME already correct for $file"
    fi
done

echo "Done!"
