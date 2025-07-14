# Download the zip file
wget https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0.zip

# Verify the file integrity using SHA-256
echo "6680fea5be2339ea15091a249fbd70e49551246ddbd5ca50f1b2352c08c95291  maestro-v3.0.0.zip" | sha256sum -c -

# Unzip the dataset
unzip maestro-v3.0.0.zip

# Rename all .midi files to .mid
find maestro-v3.0.0 -type f -name "*.midi" | while read -r file; do
    mv "$file" "${file%.midi}.mid"
done
