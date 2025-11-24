// RASS CUISINE - JavaScript Functions

// Modal Functions
function openAddModal() {
    const modal = document.getElementById('addEmployeeModal');
    modal.classList.add('active');

    // Focus first input after a short delay
    setTimeout(() => {
        const firstInput = modal.querySelector('input[name="name"]');
        if (firstInput) {
            firstInput.focus();
        }
    }, 100);
}

function closeAddModal() {
    document.getElementById('addEmployeeModal').classList.remove('active');
}

function openEditModal(employeeId) {
    const modal = document.getElementById('editEmployeeModal');
    const form = document.getElementById('editEmployeeForm');

    // Fetch employee data
    fetch(`/employee/${employeeId}/data`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('edit_name').value = data.name;
            document.getElementById('edit_designation').value = data.designation;
            document.getElementById('edit_salary').value = data.salary;
            document.getElementById('edit_join_date').value = data.join_date;

            form.action = `/employee/edit/${employeeId}`;
            modal.classList.add('active');

            // Focus first input after modal opens
            setTimeout(() => {
                document.getElementById('edit_name').focus();
            }, 100);
        })
        .catch(error => {
            console.error('Error fetching employee data:', error);
            alert('Error loading employee data');
        });
}

function closeEditModal() {
    document.getElementById('editEmployeeModal').classList.remove('active');
}

function openWithdrawalModal(employeeId, employeeName, totalSalary, withdrawn) {
    const modal = document.getElementById('withdrawalModal');
    const salaryInfo = document.getElementById('salaryInfo');
    const remaining = totalSalary - withdrawn;

    // Format numbers with commas
    const formatNumber = (num) => {
        return num.toLocaleString('en-IN', { maximumFractionDigits: 0 });
    };

    salaryInfo.innerHTML = `
        <h4 class="font-semibold text-gray-800 mb-3">Salary Details for ${employeeName}</h4>
        <div class="space-y-2 text-sm">
            <div class="flex justify-between">
                <span class="text-gray-600">Total Salary:</span>
                <span class="font-semibold text-green-600">Rs ${formatNumber(totalSalary)}</span>
            </div>
            <div class="flex justify-between">
                <span class="text-gray-600">Already Withdrawn:</span>
                <span class="font-semibold text-orange-600">Rs ${formatNumber(withdrawn)}</span>
            </div>
            <div class="flex justify-between pt-2 border-t border-orange-200">
                <span class="text-gray-700 font-medium">Remaining Balance:</span>
                <span class="font-bold text-blue-600">Rs ${formatNumber(remaining)}</span>
            </div>
        </div>
    `;

    document.getElementById('withdrawal_employee_id').value = employeeId;
    document.getElementById('withdrawal_amount').max = remaining;
    document.getElementById('withdrawal_amount').value = '';

    modal.classList.add('active');

    // Focus on amount input after modal opens
    setTimeout(() => {
        document.getElementById('withdrawal_amount').focus();
    }, 100);
}

function closeWithdrawalModal() {
    document.getElementById('withdrawalModal').classList.remove('active');
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.classList.remove('active');
        }
    });
}

// Close modals with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.remove('active');
        });
    }
});

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 300);
        }, 5000);
    });
});

// Form validation
function validateWithdrawal() {
    const amount = parseFloat(document.getElementById('withdrawal_amount').value);
    const maxAmount = parseFloat(document.getElementById('withdrawal_amount').max);

    if (amount > maxAmount) {
        alert(`Withdrawal amount cannot exceed remaining balance (Rs ${maxAmount.toLocaleString()})`);
        return false;
    }

    if (amount <= 0) {
        alert('Please enter a valid withdrawal amount');
        return false;
    }

    return true;
}

// Add loading spinner to buttons on form submit
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = `
                    <svg class="animate-spin h-5 w-5 inline mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                `;

                // Re-enable after 5 seconds in case of error
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 5000);
            }
        });
    });
});

// Number formatting for currency inputs
function formatCurrency(input) {
    let value = input.value.replace(/,/g, '');
    if (!isNaN(value) && value !== '') {
        input.value = parseFloat(value).toLocaleString('en-IN');
    }
}

// Search functionality with debounce
let searchTimeout;
function debounceSearch(input) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        input.form.submit();
    }, 500);
}

// Confirm before delete
function confirmDelete(employeeName) {
    return confirm(`Are you sure you want to delete ${employeeName}? This action cannot be undone and will also delete all associated transactions.`);
}

// Print functionality
function printReport() {
    window.print();
}

// Export to PDF (using browser's print to PDF)
function exportToPDF() {
    window.print();
}

// Password strength indicator
function checkPasswordStrength(password) {
    let strength = 0;

    if (password.length >= 8) strength++;
    if (password.match(/[a-z]/)) strength++;
    if (password.match(/[A-Z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[^a-zA-Z0-9]/)) strength++;

    const strengthText = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const strengthColor = ['#ef4444', '#f59e0b', '#eab308', '#10b981', '#059669'];

    return {
        score: strength,
        text: strengthText[strength - 1] || 'Very Weak',
        color: strengthColor[strength - 1] || '#ef4444'
    };
}

// Initialize tooltips
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = tooltipText;
            document.body.appendChild(tooltip);

            const rect = this.getBoundingClientRect();
            tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
            tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
        });

        element.addEventListener('mouseleave', function() {
            const tooltip = document.querySelector('.tooltip');
            if (tooltip) tooltip.remove();
        });
    });
}

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy', 'error');
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initTooltips();

    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Console greeting
console.log(`
%c RASS CUISINE RESTAURANT 
%c Salary Management System v1.0 
%c Developed for efficient salary tracking 
`,
'color: #f97316; font-size: 20px; font-weight: bold;',
'color: #dc2626; font-size: 14px;',
'color: #6b7280; font-size: 12px;'
);