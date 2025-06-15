// Video Merger App JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const imageInput = document.getElementById('image');
    const audioInput = document.getElementById('audio');
    const previewSection = document.getElementById('previewSection');
    const imagePreview = document.getElementById('imagePreview');
    const audioPreview = document.getElementById('audioPreview');
    const imageInfo = document.getElementById('imageInfo');
    const audioInfo = document.getElementById('audioInfo');
    const progressSection = document.getElementById('progressSection');
    const submitBtn = document.getElementById('submitBtn');

    // File size formatter
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Image file handler
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif'];
                if (!allowedTypes.includes(file.type)) {
                    alert('Please select a valid image file (PNG, JPG, JPEG, GIF)');
                    this.value = '';
                    return;
                }

                // Validate file size (100MB)
                if (file.size > 100 * 1024 * 1024) {
                    alert('Image file is too large. Maximum size is 100MB.');
                    this.value = '';
                    return;
                }

                // Show preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imageInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
                    checkBothFiles();
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Audio file handler
    if (audioInput) {
        audioInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                const allowedTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/aac', 'audio/mp4'];
                if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().match(/\.(mp3|wav|aac|m4a)$/)) {
                    alert('Please select a valid audio file (MP3, WAV, AAC, M4A)');
                    this.value = '';
                    return;
                }

                // Validate file size (100MB)
                if (file.size > 100 * 1024 * 1024) {
                    alert('Audio file is too large. Maximum size is 100MB.');
                    this.value = '';
                    return;
                }

                // Show preview
                const url = URL.createObjectURL(file);
                audioPreview.src = url;
                audioInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
                checkBothFiles();
            }
        });
    }

    // Check if both files are selected
    function checkBothFiles() {
        const hasImage = imageInput && imageInput.files.length > 0;
        const hasAudio = audioInput && audioInput.files.length > 0;
        
        if (hasImage && hasAudio) {
            previewSection.style.display = 'block';
            previewSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // Form submission handler
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const imageFile = imageInput.files[0];
            const audioFile = audioInput.files[0];

            if (!imageFile || !audioFile) {
                e.preventDefault();
                alert('Please select both image and audio files.');
                return;
            }

            // Show progress
            progressSection.style.display = 'block';
            submitBtn.classList.add('btn-loading');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';

            // Scroll to progress section
            progressSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Drag and drop functionality for file inputs
    function setupDragAndDrop(inputElement, allowedTypes) {
        if (!inputElement) return;

        const container = inputElement.closest('.mb-4');
        
        container.addEventListener('dragover', function(e) {
            e.preventDefault();
            container.classList.add('border-primary');
        });

        container.addEventListener('dragleave', function(e) {
            e.preventDefault();
            container.classList.remove('border-primary');
        });

        container.addEventListener('drop', function(e) {
            e.preventDefault();
            container.classList.remove('border-primary');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                
                // Check file type
                const isValidType = allowedTypes.some(type => {
                    if (type.includes('/')) {
                        return file.type === type;
                    } else {
                        return file.name.toLowerCase().endsWith(type);
                    }
                });

                if (isValidType) {
                    // Create a new FileList and assign to input
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    inputElement.files = dt.files;
                    
                    // Trigger change event
                    const event = new Event('change', { bubbles: true });
                    inputElement.dispatchEvent(event);
                } else {
                    alert(`Invalid file type. Please select a valid ${inputElement.id} file.`);
                }
            }
        });
    }

    // Setup drag and drop for both inputs
    setupDragAndDrop(imageInput, ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', '.png', '.jpg', '.jpeg', '.gif']);
    setupDragAndDrop(audioInput, ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/aac', '.mp3', '.wav', '.aac', '.m4a']);
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
});

// Page visibility change handler (pause audio when tab is hidden)
document.addEventListener('visibilitychange', function() {
    const audioPreview = document.getElementById('audioPreview');
    if (audioPreview && document.hidden) {
        audioPreview.pause();
    }
});
