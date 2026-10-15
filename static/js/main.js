/**
 * Student Resources Management System (Student Needs Portal)
 * Main Interactive JavaScript
 * Academic Year 2026-2027 | CMCS College
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => alert.remove());
        }
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // 2. AJAX Bookmark / Save Listing Toggle
    const bookmarkBtns = document.querySelectorAll('.js-bookmark-btn');
    bookmarkBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const listingId = btn.dataset.listingId;
            if (!listingId) return;

            try {
                const response = await fetch(`/listings/${listingId}/bookmark`, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.redirected) {
                    window.location.href = response.url;
                    return;
                }

                const data = await response.json();
                if (data.success) {
                    const icon = btn.querySelector('.bookmark-icon') || btn;
                    if (data.is_saved) {
                        btn.classList.add('active');
                        icon.innerHTML = '★ Saved';
                        showToast(data.message, 'success');
                    } else {
                        btn.classList.remove('active');
                        icon.innerHTML = '☆ Save';
                        showToast(data.message, 'info');
                    }
                }
            } catch (err) {
                console.error("Bookmark error:", err);
            }
        });
    });

    // 3. Dynamic Category Form Field Visibility (Provider Add/Edit Listing)
    const categorySelector = document.getElementById('category-select');
    if (categorySelector) {
        const accommodationFields = document.getElementById('fields-accommodation');
        const messFields = document.getElementById('fields-mess');
        const libraryFields = document.getElementById('fields-library');
        const subcategorySelect = document.getElementById('subcategory-select');

        const subcategoryOptions = {
            'accommodation': [
                { val: 'Hostel', label: 'Student Hostel' },
                { val: 'PG (Paying Guest)', label: 'PG (Paying Guest)' },
                { val: 'Rental Flat / Room', label: 'Rental Room / Flat Sharing' },
                { val: 'Girls PG / Hostel', label: 'Girls Dedicated Hostel/PG' },
                { val: 'Boys PG / Hostel', label: 'Boys Dedicated Hostel/PG' }
            ],
            'mess': [
                { val: 'Pure Veg Mess', label: 'Pure Veg Homely Mess' },
                { val: 'Veg & Non-Veg Mess', label: 'Veg & Non-Veg Mess' },
                { val: 'Tiffin & Dabba Delivery', label: 'Daily Tiffin & Meal Box' },
                { val: 'South Indian & North Indian', label: 'Special South/North Indian Mess' }
            ],
            'library': [
                { val: '24/7 AC Study Library', label: '24/7 Air Conditioned Study Hall' },
                { val: 'Digital Abhyasika', label: 'Digital Abhyasika Reading Room' },
                { val: 'Exam Preparation Library', label: 'Competitive Exam & CA Reading Room' }
            ]
        };

        const updateCategoryFields = () => {
            const cat = categorySelector.value;
            if (accommodationFields) accommodationFields.style.display = (cat === 'accommodation') ? 'block' : 'none';
            if (messFields) messFields.style.display = (cat === 'mess') ? 'block' : 'none';
            if (libraryFields) libraryFields.style.display = (cat === 'library') ? 'block' : 'none';

            // Populate subcategories
            if (subcategorySelect && subcategoryOptions[cat]) {
                const currentVal = subcategorySelect.dataset.selected || '';
                subcategorySelect.innerHTML = '<option value="">Select Sub-Type...</option>';
                subcategoryOptions[cat].forEach(opt => {
                    const optionElem = document.createElement('option');
                    optionElem.value = opt.val;
                    optionElem.textContent = opt.label;
                    if (opt.val === currentVal) optionElem.selected = true;
                    subcategorySelect.appendChild(optionElem);
                });
            }
        };

        categorySelector.addEventListener('change', updateCategoryFields);
        updateCategoryFields();
    }

    // 4. Modal Triggers
    const modalOpenTriggers = document.querySelectorAll('[data-open-modal]');
    modalOpenTriggers.forEach(btn => {
        btn.addEventListener('click', () => {
            const modalId = btn.dataset.openModal;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('active');
            }
        });
    });

    const modalCloseTriggers = document.querySelectorAll('[data-close-modal], .modal-overlay');
    modalCloseTriggers.forEach(elem => {
        elem.addEventListener('click', (e) => {
            if (e.target === elem || elem.hasAttribute('data-close-modal')) {
                const activeModal = elem.closest('.modal-overlay') || elem;
                if (activeModal.classList.contains('modal-overlay')) {
                    activeModal.classList.remove('active');
                }
            }
        });
    });

    // 5. Comparison Tool Helper (Stores IDs in localStorage and navigates)
    const compareCheckboxes = document.querySelectorAll('.js-compare-check');
    const compareBar = document.getElementById('compare-floating-bar');
    const compareCountSpan = document.getElementById('compare-count');
    const compareBtn = document.getElementById('btn-go-compare');

    if (compareCheckboxes.length > 0) {
        let selectedCompareIds = JSON.parse(localStorage.getItem('compare_listings') || '[]');

        // Check boxes initially if in localStorage
        compareCheckboxes.forEach(cb => {
            if (selectedCompareIds.includes(parseInt(cb.value))) {
                cb.checked = true;
            }
            cb.addEventListener('change', () => {
                const id = parseInt(cb.value);
                if (cb.checked) {
                    if (selectedCompareIds.length >= 4) {
                        alert("You can compare up to 4 services side-by-side.");
                        cb.checked = false;
                        return;
                    }
                    if (!selectedCompareIds.includes(id)) selectedCompareIds.push(id);
                } else {
                    selectedCompareIds = selectedCompareIds.filter(x => x !== id);
                }
                localStorage.setItem('compare_listings', JSON.stringify(selectedCompareIds));
                updateCompareUI();
            });
        });

        const updateCompareUI = () => {
            if (compareBar && compareCountSpan) {
                if (selectedCompareIds.length > 0) {
                    compareBar.style.display = 'flex';
                    compareCountSpan.textContent = selectedCompareIds.length;
                    if (compareBtn) {
                        compareBtn.href = `/compare?ids=${selectedCompareIds.join(',')}`;
                    }
                } else {
                    compareBar.style.display = 'none';
                }
            }
        };

        const clearCompareBtn = document.getElementById('btn-clear-compare');
        if (clearCompareBtn) {
            clearCompareBtn.addEventListener('click', () => {
                selectedCompareIds = [];
                localStorage.removeItem('compare_listings');
                compareCheckboxes.forEach(cb => cb.checked = false);
                updateCompareUI();
            });
        }

        updateCompareUI();
    }
});

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '10px';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    toast.style.margin = '0';
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
