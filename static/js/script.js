function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}
const csrftoken = getCookie('csrftoken');

function postCart(url, quantity) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `quantity=${quantity}`,
    }).then(res => res.json());
}

function updateFloatingCart(count, total) {
    const countEl = document.querySelector('.floating-cart .cart-count');
    const totalEl = document.querySelector('.floating-cart .cart-total');
    if (countEl) countEl.textContent = `🛒 ${count} items`;
    if (totalEl) totalEl.textContent = `৳${Math.round(total)}`;
}

function renderCartAction(container, qty) {
    // Existing Buy Now form preserve করে রাখবো
    const buyNowForm = container.querySelector('.buy-now-form');

    // Cart control নতুন করে render হবে
    container.innerHTML = '';

    if (qty > 0) {
        container.insertAdjacentHTML('afterbegin', `
            <div class="qty-stepper">
                <button type="button" class="qty-minus">−</button>
                <span class="qty-label">${qty} Cart</span>
                <button type="button" class="qty-plus">+</button>
            </div>
        `);
    } else {
        container.insertAdjacentHTML('afterbegin', `
            <button type="button" class="add-to-cart-btn">
                + Add to Cart
            </button>
        `);
    }

    // Buy Now form আবার যোগ করা হবে
    if (buyNowForm) {
        container.appendChild(buyNowForm);
    }

    attachCartActionEvents(container);
}

function attachCartActionEvents(container) {
    // ⬇️ eita mul fix: nijer moddhe url na thakle parent theke khoja hoy
    const urlSource = container.dataset.addUrl ? container : container.closest('[data-add-url]');
    if (!urlSource) return;

    const addBtn = container.querySelector('.add-to-cart-btn');
    const plusBtn = container.querySelector('.qty-plus');
    const minusBtn = container.querySelector('.qty-minus');
    const currentQtyText = container.querySelector('.qty-label');
    const currentQty = currentQtyText ? parseInt(currentQtyText.textContent) : 0;

    if (addBtn) {
        addBtn.addEventListener('click', () => {
            postCart(urlSource.dataset.addUrl, 1).then(data => {
                renderCartAction(container, data.quantity);
                updateFloatingCart(data.cart_count, data.cart_total);

                fbq('track', 'AddToCart', {
                    content_ids: [urlSource.dataset.productId],
                    content_type: 'product',
                    currency: 'BDT'
                });
            });
        });
    }
    if (plusBtn) {
        plusBtn.addEventListener('click', () => {
            postCart(urlSource.dataset.updateUrl, currentQty + 1).then(data => {
                renderCartAction(container, data.quantity);
                updateFloatingCart(data.cart_count, data.cart_total);
            });
        });
    }
    if (minusBtn) {
        minusBtn.addEventListener('click', () => {
            const newQty = currentQty - 1;
            const url = newQty > 0 ? urlSource.dataset.updateUrl : urlSource.dataset.removeUrl;
            postCart(url, newQty).then(data => {
                renderCartAction(container, data.quantity);
                updateFloatingCart(data.cart_count, data.cart_total);
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // Product card (home/category page) — nijer moddheই data attribute ache
    document.querySelectorAll('.cart-action').forEach(attachCartActionEvents);

    // Product detail page — .pd-cart-action, url tar parent '.product-detail-actions' e ache
    document.querySelectorAll('.pd-cart-action').forEach(attachCartActionEvents);

    // ---- Search Suggestions ----
    const searchInput = document.getElementById('search-input');
    const suggestionsBox = document.getElementById('search-suggestions');

    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            const query = this.value.trim();
            if (query.length === 0) {
                suggestionsBox.style.display = 'none';
                suggestionsBox.innerHTML = '';
                return;
            }
            debounceTimer = setTimeout(() => {
                fetch(`/search-suggestions/?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        suggestionsBox.innerHTML = '';
                        if (data.results.length === 0) {
                            suggestionsBox.style.display = 'none';
                            return;
                        }
                        data.results.forEach(item => {
                            const a = document.createElement('a');
                            a.href = item.url;
                            a.innerHTML = `
                                ${item.image ? `<img src="${item.image}">` : '<div style="width:38px;height:38px;background:#eee;border-radius:6px;"></div>'}
                                <span>
                                    <span class="s-name">${item.name}</span><br>
                                    <span class="s-price">৳${item.price}</span>
                                </span>`;
                            suggestionsBox.appendChild(a);
                        });
                        suggestionsBox.style.display = 'block';
                    });
            }, 300);
        });
        document.addEventListener('click', function (e) {
            if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                suggestionsBox.style.display = 'none';
            }
        });
    }
    // ---- Category Nav Marquee (dynamic speed) ----
    const catTrack = document.getElementById('categoryNavTrack');
    if (catTrack && catTrack.children.length > 1) {
        const pxPerSecond = 35;
        const singleSetWidth = catTrack.scrollWidth / 2;
        const duration = singleSetWidth / pxPerSecond;
        catTrack.style.animationDuration = `${duration}s`;
    }
});
