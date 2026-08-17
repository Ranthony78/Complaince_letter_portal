import os
import requests
from pathlib import Path

# 🔧 CHANGE THIS PATH to your Django static directory
BASE_DIR = r"D:\DjangoApplication\complianceletterportalapp\static"

# 📁 Create folder structure
folders = [
    "css",
    "js",
    "images",
    "fonts",
    "webfonts",
    "icons/fontawesome/css",
    "icons/fontawesome/webfonts",
    "datatables/css",
    "datatables/js",
    "select2/css",
    "select2/js",
    "chartjs"
]

# Create all folders
for folder in folders:
    os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)
    print(f"📁 Created folder: {folder}")

# 📦 Complete files to download (based on your base.html)
files = {
    # ========== BOOTSTRAP 5 ==========
    "css/bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
    "css/bootstrap.min.css.map": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css.map",
    "js/bootstrap.bundle.min.js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
    "js/bootstrap.bundle.min.js.map": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js.map",

    # ========== JQUERY ==========
    "js/jquery.min.js": "https://code.jquery.com/jquery-3.6.4.min.js",
    "js/jquery-3.6.4.min.js": "https://code.jquery.com/jquery-3.6.4.min.js",

    # ========== FONT AWESOME 6 ==========
    "icons/fontawesome/css/all.min.css": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",

    # Font Awesome Web Fonts
    "icons/fontawesome/webfonts/fa-solid-900.woff2": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-solid-900.woff2",
    "icons/fontawesome/webfonts/fa-solid-900.woff": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-solid-900.woff",
    "icons/fontawesome/webfonts/fa-solid-900.ttf": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-solid-900.ttf",
    "icons/fontawesome/webfonts/fa-regular-400.woff2": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-regular-400.woff2",
    "icons/fontawesome/webfonts/fa-regular-400.woff": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-regular-400.woff",
    "icons/fontawesome/webfonts/fa-regular-400.ttf": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-regular-400.ttf",
    "icons/fontawesome/webfonts/fa-brands-400.woff2": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-brands-400.woff2",
    "icons/fontawesome/webfonts/fa-brands-400.woff": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-brands-400.woff",
    "icons/fontawesome/webfonts/fa-brands-400.ttf": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-brands-400.ttf",
    "icons/fontawesome/webfonts/fa-v4compatibility.woff2": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-v4compatibility.woff2",
    "icons/fontawesome/webfonts/fa-v4compatibility.woff": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-v4compatibility.woff",

    # ========== DATATABLES ==========
    "datatables/css/dataTables.bootstrap5.min.css": "https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css",
    "datatables/js/jquery.dataTables.min.js": "https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js",
    "datatables/js/dataTables.bootstrap5.min.js": "https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js",

    # DataTables images (optional but good for legacy)
    "datatables/images/sort_asc.png": "https://cdn.datatables.net/1.13.4/images/sort_asc.png",
    "datatables/images/sort_desc.png": "https://cdn.datatables.net/1.13.4/images/sort_desc.png",
    "datatables/images/sort_both.png": "https://cdn.datatables.net/1.13.4/images/sort_both.png",

    # ========== SELECT2 ==========
    "select2/css/select2.min.css": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
    "select2/css/select2-bootstrap-5-theme.min.css": "https://cdn.jsdelivr.net/npm/select2-bootstrap-5-theme@1.3.0/dist/select2-bootstrap-5-theme.min.css",
    "select2/js/select2.min.js": "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js",

    # ========== CHART.JS ==========
    "chartjs/chart.umd.min.js": "https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.umd.min.js",
    "chartjs/chart.umd.js": "https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.umd.js",

    # ========== GOOGLE FONTS ==========
    "fonts/inter.css": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    "fonts/poppins.css": "https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&display=swap",

    # ========== BOOTSTRAP ICONS (Optional but useful) ==========
    "css/bootstrap-icons.min.css": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.min.css",
    "fonts/bootstrap-icons.woff2": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/fonts/bootstrap-icons.woff2",
    "fonts/bootstrap-icons.woff": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/fonts/bootstrap-icons.woff",
}

# Alternative CDN URLs in case primary fails
fallback_urls = {
    "js/jquery.min.js": "https://ajax.googleapis.com/ajax/libs/jquery/3.6.4/jquery.min.js",
    "css/bootstrap.min.css": "https://stackpath.bootstrapcdn.com/bootstrap/5.3.0/css/bootstrap.min.css",
}


def download_file(path, url, retry=True):
    """Download file with retry and fallback support"""
    full_path = os.path.join(BASE_DIR, path)

    # Skip if file already exists and is not empty
    if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
        print(f"⏭️  Already exists: {path}")
        return True

    try:
        print(f"📥 Downloading: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "wb") as f:
                f.write(response.content)

            file_size = os.path.getsize(full_path)
            print(f"✅ Saved → {path} ({file_size:,} bytes)")
            return True
        else:
            print(f"❌ Failed ({response.status_code}): {url}")

            # Try fallback URL if available
            if retry and path in fallback_urls:
                print(f"🔄 Trying fallback URL for {path}")
                return download_file(path, fallback_urls[path], retry=False)

            return False

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error downloading {url}: {e}")

        # Try fallback URL if available
        if retry and path in fallback_urls:
            print(f"🔄 Trying fallback URL for {path}")
            return download_file(path, fallback_urls[path], retry=False)

        return False


def create_sample_css_files():
    """Create sample CSS files if they don't exist"""
    sample_css_files = {
        "css/theme.css": """/* Custom Theme */
:root {
    --primary-color: #0d6efd;
    --secondary-color: #6c757d;
    --success-color: #198754;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
    --info-color: #0dcaf0;
}

body {
    font-family: 'Inter', sans-serif;
}

.sidebar {
    background-color: #2c3e50;
    color: white;
}

.main-content {
    margin-left: 250px;
    padding: 20px;
}
""",
        "css/style.css": """/* Custom Styles */
.container-fluid {
    max-width: 1400px;
}

.breadcrumb {
    background: transparent;
    padding: 0;
}

.card {
    border-radius: 10px;
    box-shadow: 0 0 20px rgba(0,0,0,0.08);
    transition: transform 0.2s;
}

.card:hover {
    transform: translateY(-5px);
}

.btn {
    border-radius: 5px;
    padding: 8px 20px;
}

.table-responsive {
    border-radius: 10px;
    overflow: hidden;
}
""",
        "css/dashboard.css": """/* Dashboard Specific Styles */
.dashboard-stats {
    margin-bottom: 30px;
}

.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
}

.stat-card i {
    font-size: 3rem;
    opacity: 0.3;
}

.chart-container {
    position: relative;
    height: 300px;
    margin-bottom: 20px;
}
""",
        "js/main.js": """// Main JavaScript file
$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Add active class to current nav item
    var currentLocation = window.location.pathname;
    $('.sidebar-nav a').each(function() {
        if ($(this).attr('href') === currentLocation) {
            $(this).addClass('active');
        }
    });
});

// Loading overlay functions
function showLoading() {
    $('#loadingModal').modal('show');
}

function hideLoading() {
    $('#loadingModal').modal('hide');
}

// AJAX setup for CSRF token
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
"""
    }

    for file_path, content in sample_css_files.items():
        full_path = os.path.join(BASE_DIR, file_path)
        if not os.path.exists(full_path):
            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"📝 Created sample file: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not create {file_path}: {e}")


def create_directory_structure_report():
    """Generate a report of downloaded files"""
    report_path = os.path.join(BASE_DIR, "static_files_report.txt")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Static Files Download Report\n")
        f.write("=" * 50 + "\n\n")

        for root, dirs, files in os.walk(BASE_DIR):
            rel_path = os.path.relpath(root, BASE_DIR)
            if rel_path == '.':
                rel_path = 'root'

            f.write(f"\n📁 {rel_path}/\n")
            for file in files:
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                f.write(f"  📄 {file} ({size:,} bytes)\n")

    print(f"\n📊 Report saved to: {report_path}")


# Main execution
if __name__ == "__main__":
    print("🚀 Starting static files download...")
    print(f"📂 Base directory: {BASE_DIR}\n")

    # Download all files
    successful = 0
    failed = 0

    for path, url in files.items():
        if download_file(path, url):
            successful += 1
        else:
            failed += 1

    # Create sample CSS/JS files
    print("\n📝 Creating sample CSS/JS files...")
    create_sample_css_files()

    # Print summary
    print("\n" + "=" * 50)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"✅ Successful downloads: {successful}")
    print(f"❌ Failed downloads: {failed}")
    print(f"📁 Total files in static directory: {sum(len(files) for _, _, files in os.walk(BASE_DIR))}")

    # Create report
    create_directory_structure_report()

    print("\n🎉 All static files have been processed!")
    print("\n💡 Next steps:")
    print("1. Update your Django settings to use local static files")
    print("2. Run 'python manage.py collectstatic' if needed")
    print("3. Update your base.html to reference local files instead of CDNs")