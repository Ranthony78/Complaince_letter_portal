// static/js/main.js
$(document).ready(function() {
    // Sidebar Toggle
    $('#sidebarToggle').click(function() {
        $('#sidebar').toggleClass('show');
        $(this).find('i').toggleClass('fa-bars fa-times');
    });

    // Initialize Select2
    $('.select2').select2({
        theme: 'bootstrap-5',
        width: '100%',
        placeholder: 'Select an option',
        allowClear: true
    });

    // Initialize DataTables safely
    try {
        $('.datatable').each(function() {
            const $table = $(this);
            const headerCols = $table.find('thead th').length;
            const firstBodyRowCols = $table.find('tbody tr:first td').length;

            if (headerCols === firstBodyRowCols && headerCols > 0) {
                $table.DataTable({
                    responsive: true,
                    language: {
                        search: "_INPUT_",
                        searchPlaceholder: "Search...",
                        lengthMenu: "Show _MENU_ entries",
                        info: "Showing _START_ to _END_ of _TOTAL_ entries",
                        paginate: {
                            first: '<i class="fas fa-angle-double-left"></i>',
                            previous: '<i class="fas fa-angle-left"></i>',
                            next: '<i class="fas fa-angle-right"></i>',
                            last: '<i class="fas fa-angle-double-right"></i>'
                        }
                    },
                    pageLength: 25,
                    order: [[0, 'desc']],
                    columnDefs: [
                        { orderable: false, targets: -1 }
                    ]
                });
            } else {
                console.warn('Table column count mismatch, skipping DataTables initialization');
                $table.removeClass('datatable');
            }
        });
    } catch(e) {
        console.warn('DataTables initialization error:', e.message);
    }

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Add active class to current nav item
    const currentPath = window.location.pathname;
    $('.sidebar .nav-link').each(function() {
        const href = $(this).attr('href');
        if (href && currentPath === href) {
            $(this).addClass('active');
        }
    });

    // Tooltips initialization
    $('[data-toggle="tooltip"]').tooltip();
});

function showLoading() {
    $('#loadingOverlay').fadeIn();
}

function hideLoading() {
    $('#loadingOverlay').fadeOut();
}

// Handle window resize
$(window).on('resize', function() {
    if ($(window).width() > 768) {
        $('#sidebar').removeClass('show');
    }
});

