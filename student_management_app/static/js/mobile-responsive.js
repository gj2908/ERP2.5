/**
 * Mobile Responsiveness Script
 * This script enhances the mobile experience for the admin dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
  
  // Function to check if the device is mobile
  function isMobileDevice() {
    return window.innerWidth < 768;
  }
  
  // Add mobile class to body if on mobile device
  if (isMobileDevice()) {
    document.body.classList.add('mobile-view');
  }
  
  // Mobile sidebar toggling
  if (isMobileDevice()) {
    // Ensure sidebar is closed by default on mobile
    if (document.body.classList.contains('sidebar-open')) {
      document.body.classList.remove('sidebar-open');
    }
    
    // Improve navbar toggle button functionality
    var navbarToggler = document.querySelector('.navbar-toggler, [data-widget="pushmenu"]');
    if (navbarToggler) {
      navbarToggler.addEventListener('click', function(e) {
        // Let AdminLTE handle this, don't interfere
      });
    }
    
    // Close sidebar when clicking outside
    document.addEventListener('click', function(e) {
      if (document.body.classList.contains('sidebar-open')) {
        const sidebar = document.querySelector('.main-sidebar');
        const navbarToggler = document.querySelector('.navbar-toggler, [data-widget="pushmenu"]');
        
        if (sidebar && !sidebar.contains(e.target) && 
            navbarToggler && !navbarToggler.contains(e.target)) {
          document.body.classList.remove('sidebar-open');
        }
      }
    });
    
    // Don't interfere with sidebar menu items to preserve dropdown functionality
  }
  
  // Make tables responsive
  function makeTablesResponsive() {
    const tables = document.querySelectorAll('table:not(.table-no-responsive)');
    tables.forEach(function(table) {
      // Skip tables that are already in responsive containers
      if (!table.closest('.table-responsive') && !table.classList.contains('dataTable')) {
        // Wrap tables in responsive container if not already wrapped
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
      }
    });
  }
  
  // Call initially
  makeTablesResponsive();
  
  // Also call after AJAX content is loaded (for dynamically added tables)
  $(document).ajaxComplete(function() {
    setTimeout(makeTablesResponsive, 100);
  });
  
  // Fix for modals on mobile
  const modals = document.querySelectorAll('.modal');
  modals.forEach(function(modal) {
    // Ensure modals are properly scrollable on mobile
    modal.addEventListener('shown.bs.modal', function() {
      if (isMobileDevice()) {
        modal.style.paddingLeft = '0';
        modal.style.paddingRight = '0';
      }
    });
  });
  
  // Enhance form controls on mobile
  if (isMobileDevice()) {
    // Adjust select inputs for better mobile experience
    const selects = document.querySelectorAll('select.form-control');
    selects.forEach(function(select) {
      select.classList.add('mobile-select');
    });
    
    // Improve date inputs
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
      input.classList.add('mobile-date-input');
    });
    
    // Add action column class to last column in action tables
    function markActionColumns() {
      const tables = document.querySelectorAll('table');
      tables.forEach(function(table) {
        // Check for tables with buttons or action links in the last column
        const rows = table.querySelectorAll('tr');
        let hasActionButtons = false;
        
        // Check if the last column contains buttons
        rows.forEach(function(row) {
          const cells = row.querySelectorAll('td, th');
          if (cells.length > 0) {
            const lastCell = cells[cells.length - 1];
            // Check if it contains actions (buttons, links, icons)
            if (lastCell.querySelector('.btn, a, button, .fa, .fas, .far, .fab')) {
              hasActionButtons = true;
            }
          }
        });
        
        // If the table has action buttons in the last column, mark them all
        if (hasActionButtons) {
          rows.forEach(function(row) {
            const cells = row.querySelectorAll('td, th');
            if (cells.length > 0) {
              const lastCell = cells[cells.length - 1];
              lastCell.classList.add('action-column');
            }
          });
        }
      });
    }
    
    // Call initially and after any potential AJAX load
    markActionColumns();
    
    $(document).ajaxComplete(function() {
      setTimeout(markActionColumns, 100);
    });
    
    // Improve card headers with buttons
    const cardHeaders = document.querySelectorAll('.card-header');
    cardHeaders.forEach(function(header) {
      const tools = header.querySelector('.card-tools');
      if (tools && isMobileDevice()) {
        header.classList.add('card-header-mobile');
      }
    });
    
    // Fix input group on mobile
    const inputGroups = document.querySelectorAll('.input-group');
    inputGroups.forEach(function(group) {
      group.classList.add('input-group-mobile');
    });
  }
  
  // Handle orientation changes
  window.addEventListener('orientationchange', function() {
    // Adjust layout after orientation change
    setTimeout(function() {
      if (isMobileDevice()) {
        // Recalculate table-responsive elements
        makeTablesResponsive();
      }
    }, 200);
  });
  
  // Mobile-friendly DataTables configuration
  if (typeof $.fn.DataTable !== 'undefined') {
    $.extend(true, $.fn.DataTable.defaults, {
      responsive: true,
      language: {
        search: "_INPUT_",
        searchPlaceholder: "Search...",
        lengthMenu: "_MENU_",
        info: "Showing _START_ to _END_ of _TOTAL_ entries"
      },
      initComplete: function(settings, json) {
        if (isMobileDevice()) {
          // Simplify DataTable controls on mobile
          var wrapper = $(this).closest('.dataTables_wrapper');
          wrapper.find('.dataTables_length').addClass('mb-2');
          wrapper.find('.dataTables_filter').addClass('mb-2');
          wrapper.find('.dataTables_filter input').attr('placeholder', 'Search...');
        }
      }
    });
  }
  
  // Double tap prevention for buttons (prevents accidental double submissions)
  const submitButtons = document.querySelectorAll('button[type="submit"], input[type="submit"]');
  submitButtons.forEach(function(button) {
    button.addEventListener('click', function(e) {
      if (this.classList.contains('disabled')) {
        e.preventDefault();
        return false;
      }
      this.classList.add('disabled');
      // Re-enable after delay for accidental second tap
      setTimeout(() => {
        this.classList.remove('disabled');
      }, 2000);
    });
  });
  
  // Auto-collapse long text in cards with show more/less button
  if (isMobileDevice()) {
    const longTexts = document.querySelectorAll('.card-body p, .card-body .card-text');
    longTexts.forEach(function(text) {
      if (text.textContent.length > 120) {
        const originalText = text.textContent;
        const shortenedText = originalText.substring(0, 120) + '...';
        
        text.textContent = shortenedText;
        text.classList.add('text-truncated');
        
        // Create show more button
        const showMoreButton = document.createElement('button');
        showMoreButton.textContent = 'Show more';
        showMoreButton.className = 'btn btn-sm btn-link p-0 ml-1';
        text.parentNode.insertBefore(showMoreButton, text.nextSibling);
        
        showMoreButton.addEventListener('click', function() {
          if (text.classList.contains('text-truncated')) {
            text.textContent = originalText;
            text.classList.remove('text-truncated');
            this.textContent = 'Show less';
          } else {
            text.textContent = shortenedText;
            text.classList.add('text-truncated');
            this.textContent = 'Show more';
          }
        });
      }
    });
  }
  
  // Fix scrolling issues on iOS
  if (isMobileDevice() && /iPad|iPhone|iPod/.test(navigator.userAgent)) {
    document.documentElement.style.setProperty('--webkit-overflow-scrolling', 'touch');
    
    // Fix for fixed elements
    const fixedElements = document.querySelectorAll('.fixed-top, .sticky-top, .navbar-fixed-top');
    fixedElements.forEach(function(element) {
      element.style.transform = 'translateZ(0)';
    });
  }
  
  // Optimize images on mobile
  if (isMobileDevice()) {
    const images = document.querySelectorAll('img:not(.no-optimize)');
    images.forEach(function(img) {
      img.classList.add('img-fluid');
      img.setAttribute('loading', 'lazy');
    });
  }
});

// Fix for AdminLTE sidebar dropdowns
$(document).ready(function() {
  // Re-initialize AdminLTE Treeview to ensure dropdowns work
  $('[data-widget="treeview"]').each(function() {
    if (typeof $(this).Treeview !== 'undefined') {
      $(this).Treeview('init');
    }
  });
}); 