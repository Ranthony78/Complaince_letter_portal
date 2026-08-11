// static/js/theme.js - Theme Switcher
$(document).ready(function() {
    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('letter_portal_theme');
    if (savedTheme) {
        document.body.className = savedTheme;
    }
});

function changeTheme(themeName) {
    // Remove all theme classes
    document.body.classList.remove(
        'theme-blue-ocean',
        'theme-green-forest',
        'theme-sunset-orange',
        'theme-midnight-blue',
        'theme-pink-passion',
        'theme-purple-dream',
        'theme-teal-wave',
        'theme-royal-gold'
    );

    // Add new theme class
    document.body.classList.add(themeName);

    // Save to localStorage
    localStorage.setItem('letter_portal_theme', themeName);

    // Show success message
    showThemeMessage(`Theme changed to ${getThemeName(themeName)}`);
}

function getThemeName(themeClass) {
    const themes = {
        'theme-blue-ocean': 'Blue Ocean',
        'theme-green-forest': 'Green Forest',
        'theme-sunset-orange': 'Sunset Orange',
        'theme-midnight-blue': 'Midnight Blue',
        'theme-pink-passion': 'Pink Passion',
        'theme-purple-dream': 'Purple Dream',
        'theme-teal-wave': 'Teal Wave',
        'theme-royal-gold': 'Royal Gold'
    };
    return themes[themeClass] || themeClass;
}

function showThemeMessage(message) {
    // Create temporary notification
    const notification = $('<div class="theme-notification">🎨 ' + message + '</div>');
    $('body').append(notification);
    notification.fadeIn(300);
    setTimeout(function() {
        notification.fadeOut(300, function() {
            notification.remove();
        });
    }, 2000);
}

// Add theme notification styles
$('<style>.theme-notification{position:fixed;bottom:20px;right:20px;background:linear-gradient(135deg,var(--primary-start),var(--primary-middle));color:white;padding:12px 24px;border-radius:12px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.2);font-weight:500;display:none;}</style>').appendTo('head');