
const tg = window.Telegram.WebApp;
try {
  tg.ready();
  tg.expand();
  if (tg.requestFullscreen) {
    tg.requestFullscreen();
  }
  tg.setHeaderColor('#0a0a0f');
  tg.setBackgroundColor('#0a0a0f');
  tg.enableClosingConfirmation();
} catch(e) {}

const API = '';  // same origin
let userData = {};
let photoFile = null;

// ── CATEGORY & LANG (moved from inline) ──────
function setCategory(cat) {
  document.getElementById('buy-category').value = cat;
  document.getElementById('custom-word-container').style.display = (cat === 'custom') ? 'block' : 'none';
  document.getElementById('btn-cat-short').className = 'btn btn-outline';
  document.getElementById('btn-cat-smart').className = 'btn btn-outline';
  document.getElementById('btn-cat-custom').className = 'btn btn-outline';
  if(cat === 'qisqa') {
    document.getElementById('btn-cat-short').className = 'btn btn-primary';
  } else if (cat === 'turli') {
    document.getElementById('btn-cat-smart').className = 'btn btn-primary';
  } else if (cat === 'custom') {
    document.getElementById('btn-cat-custom').className = 'btn btn-primary';
  }
}
function setLang(lang) {
  document.getElementById('buy-lang').value = lang;
  if(lang === 'uz') {
    document.getElementById('btn-lang-uz').className = 'btn btn-primary';
    document.getElementById('btn-lang-en').className = 'btn btn-outline';
  } else {
    document.getElementById('btn-lang-uz').className = 'btn btn-outline';
    document.getElementById('btn-lang-en').className = 'btn btn-primary';
  }
}

// ── INIT ──────────────────────────────────────
async function init() {
  const tgUser = tg.initDataUnsafe?.user;
  if (tgUser) {
    document.getElementById('user-name').textContent = tgUser.first_name || 'Foydalanuvchi';
  }
  await loadUserData();
  await loadOrders();
  loadCardNumber();
  
  const urlParams = new URLSearchParams(window.location.search);
  const escrowId = urlParams.get('escrow');
  if (escrowId) {
    goPage('market');
    buyListing(parseInt(escrowId));
  }
}

async function loadUserData() {
  try {
    const res = await fetch(`${API}/api/user?init_data=${encodeURIComponent(tg.initData)}`);
    if (!res.ok) return;
    userData = await res.json();
    const bal = userData.balance || 0;
    
    // Global prices for confirms
    window.APP_PRICES = { 
      premium: userData.premium_price || 20000, 
      monitor: userData.monitor_price || 10000, 
      listing: userData.listing_price || 1000 
    };
    
    // Update UI Labels
    if(document.getElementById('lbl-premium-price')) document.getElementById('lbl-premium-price').textContent = window.APP_PRICES.premium.toLocaleString();
    if(document.getElementById('lbl-monitor-price')) document.getElementById('lbl-monitor-price').textContent = window.APP_PRICES.monitor.toLocaleString();
    if(document.getElementById('lbl-listing-price')) document.getElementById('lbl-listing-price').textContent = window.APP_PRICES.listing.toLocaleString();

    document.getElementById('home-balance').textContent = bal.toLocaleString();
    document.getElementById('bal-amount').textContent = bal.toLocaleString();
    document.getElementById('stat-orders').textContent = userData.total_orders || 0;
    document.getElementById('stat-usernames').textContent = userData.total_usernames || 0;
    if(document.getElementById('ref-count-val')) document.getElementById('ref-count-val').textContent = (userData.referral_count || 0) + ' ta';
    if(document.getElementById('ref-link-input')) document.getElementById('ref-link-input').value = userData.ref_link || '';

    if (userData.session_string) {
      document.getElementById('status-dot').className = 'status-dot connected';
      
      let nameText = '✅ Akkaunt ulangan';
      if (userData.is_premium) {
        nameText = '👑 Premium Akkaunt';
        const pwrap = document.getElementById('premium-wrap');
        pwrap.innerHTML = `<div style="font-weight:700; font-size:16px; margin-bottom:8px; color:#fbbf24;">👑 Premium Akkaunt</div>
                           <div style="font-size:13px; color:var(--muted);">Sizda premium yoqilgan. Tugash vaqti: ${userData.premium_until}</div>`;
      }
      
      document.getElementById('account-name').textContent = nameText;
      document.getElementById('account-sub').textContent = 'Username band qilishga tayyor';
      document.getElementById('session-form-wrap').style.display = 'none';
      document.getElementById('disconnect-wrap').style.display = 'block';
      document.getElementById('no-session-warn').style.display = 'none';
      
      document.getElementById('seller-balance-wrap').style.display = 'block';
      document.getElementById('seller-balance-amount').textContent = (userData.seller_balance || 0).toLocaleString() + ' so\'m';
      
      document.getElementById('subscriptions-wrap').style.display = 'block';
      
      loadMyUsernames();
      loadSubscriptions();
    } else {
      document.getElementById('no-session-warn').style.display = 'block';
      document.getElementById('seller-balance-wrap').style.display = 'none';
      document.getElementById('my-usernames-wrap').style.display = 'none';
      document.getElementById('subscriptions-wrap').style.display = 'none';
    }
  } catch(e) { console.error(e); }
}

async function loadMyUsernames() {
  document.getElementById('my-usernames-wrap').style.display = 'block';
  const listEl = document.getElementById('my-usernames-list');
  try {
    const res = await fetch(`${API}/api/account/usernames?init_data=${encodeURIComponent(tg.initData)}`);
    const d = await res.json();
    if (d.usernames && d.usernames.length > 0) {
      listEl.innerHTML = d.usernames.map(u => `
        <div class="order-item" style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700;">@${u.username}</div>
            <div style="font-size:12px; color:var(--muted);">${u.title}</div>
          </div>
          ${u.is_listed 
            ? `<div class="btn btn-outline" style="padding:6px 12px; width:auto; font-size:12px; margin:0; opacity:0.5; pointer-events:none; border-color:var(--success); color:var(--success);">Sotuvga qo'yilgan</div>`
            : `<button class="btn btn-outline" style="padding:6px 12px; width:auto; font-size:12px; margin:0;" onclick="listUsername('${u.username}')">Sotish</button>`
          }
        </div>
      `).join('');
    } else {
      listEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted);">Sizda bo\'sh usernamelar yo\'q</div>';
    }
  } catch(e) {
    listEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--danger);">Yuklashda xato</div>';
  }
}

async function submitWithdraw() {
  const amount = parseInt(document.getElementById('withdraw-amount').value);
  const card_number = document.getElementById('withdraw-card').value;
  const card_owner = document.getElementById('withdraw-name').value;
  
  if (!amount || !card_number || !card_owner) { showToast("Barcha maydonlarni to'ldiring", "error"); return; }
  
  const btn = event.target;
  btn.disabled = true;
  btn.innerText = "Yuborilmoqda...";
  try {
    const res = await fetch(`${API}/api/seller/withdraw`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, amount, card_number, card_owner})
    });
    const d = await res.json();
    if(d.ok) {
      showToast(d.message || "So'rov yuborildi!", "success");
      document.getElementById('withdraw-form').style.display = 'none';
      document.getElementById('seller-action-btns').style.display = 'flex';
      loadUserData();
    } else {
      showToast(d.error, "error");
    }
  } catch(e) { showToast("Xato", "error"); }
  btn.disabled = false;
  btn.innerText = "✅ Tasdiqlash";
}

async function submitTransferToMain() {
  const amount = parseInt(document.getElementById('transfer-amount').value);
  if (!amount || amount < 1000) { showToast("Minimal summa: 1,000 so'm", "error"); return; }
  
  const btn = event.target;
  btn.disabled = true;
  btn.innerText = "O'tkazilmoqda...";
  try {
    const res = await fetch(`${API}/api/seller/transfer`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({init_data: tg.initData, amount})
    });
    const d = await res.json();
    if(d.ok) {
      showToast(`✅ ${amount.toLocaleString()} so'm asosiy balansga o'tkazildi!`, "success");
      document.getElementById('transfer-form').style.display = 'none';
      document.getElementById('seller-action-btns').style.display = 'flex';
      document.getElementById('transfer-amount').value = '';
      loadUserData();
    } else {
      showToast(d.error, "error");
    }
  } catch(e) { showToast("Xato", "error"); }
  btn.disabled = false;
  btn.innerText = "✅ O'tkazish";
}

function copyRefLink() {
  const input = document.getElementById('ref-link-input');
  if (input && input.value) {
    navigator.clipboard?.writeText(input.value);
    showToast("📋 Referral havola nusxalandi!", "success");
  }
}

async function placeAuctionBid(listingId, currentBid) {
  const minBid = currentBid + 1000;
  const bidStr = prompt(`⚡ AUKSION STAVKASI\n\nJoriy eng yuqori stavka: ${currentBid.toLocaleString()} so'm\nMinimal yangi stavka: ${minBid.toLocaleString()} so'm\n\nYangi stavka summasini kiriting (so'm):`, minBid);
  if (!bidStr) return;
  const bidAmount = parseInt(bidStr);
  if (!bidAmount || bidAmount < minBid) {
    showToast(`Stavka kamida ${minBid.toLocaleString()} so'm bo'lishi kerak`, 'error');
    return;
  }
  
  try {
    const res = await fetch(`${API}/api/auction/bid`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({init_data: tg.initData, listing_id: listingId, bid_amount: bidAmount})
    });
    const d = await res.json();
    if(d.ok) {
      showToast(`⚡ Stavka qabul qilindi! (${bidAmount.toLocaleString()} so'm)`, 'success');
      loadMarketplace(true);
    } else {
      showToast(d.error || 'Xatolik', 'error');
    }
  } catch(e) { showToast('Xato yuz berdi', 'error'); }
}

async function listUsername(username) {
  const listingPriceStr = window.APP_PRICES ? window.APP_PRICES.listing.toLocaleString() : '1,000';
  const priceStr = prompt(`@${username} ni qanchaga sotmoqchisiz?\n(E'lon berish narxi ${listingPriceStr} so'm, sotilganda 10% komissiya olinadi)`, "50000");
  if (!priceStr) return;
  const price = parseInt(priceStr);
  if (isNaN(price) || price < 1000) { alert("Xato narx kiritildi!"); return; }
  
  if (!confirm(`Haqiqatdan ham @${username} ni ${price.toLocaleString()} so'mga sotuvga qo'yib, balansingizdan ${listingPriceStr} so'm e'lon to'lovini yechishga rozimisiz?`)) return;
  
  try {
    const res = await fetch(`${API}/api/marketplace/list`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, username, price})
    });
    const d = await res.json();
    if(d.ok) {
      showToast("E'lon qo'shildi!", "success");
      loadUserData();
      goPage('market');
    } else {
      showToast(d.error, "error");
    }
  } catch(e) { showToast("Xato", "error"); }
}

let currentMarketOffset = 0;

async function loadMarketplace(reset = true) {
  document.getElementById('btn-market-all').className = 'btn btn-primary';
  document.getElementById('btn-market-my').className = 'btn btn-outline';
  document.getElementById('market-sort-container').style.display = 'block';
  
  if (reset) {
    currentMarketOffset = 0;
    document.getElementById('market-search').value = '';
  }
  
  const sort = document.getElementById('market-sort').value;
  const listEl = document.getElementById('market-list');
  const loadMoreEl = document.getElementById('market-load-more');
  const loadMoreBtn = document.getElementById('btn-load-more');
  
  if (reset) {
    // Shimmer skeleton
    listEl.innerHTML = `<div class="market-grid">${Array(4).fill(`
      <div class="market-card" style="pointer-events:none;">
        <div class="skeleton" style="width:48px;height:48px;border-radius:50%;margin:0 auto 10px;"></div>
        <div class="skeleton" style="height:14px;width:70%;margin:0 auto 6px;"></div>
        <div class="skeleton" style="height:10px;width:50%;margin:0 auto 10px;"></div>
        <div class="skeleton" style="height:36px;border-radius:12px;margin-bottom:8px;"></div>
        <div class="skeleton" style="height:30px;border-radius:12px;"></div>
      </div>`).join('')}</div>`;
    loadMoreEl.style.display = 'none';
  } else {
    loadMoreBtn.innerText = 'Yuklanmoqda...';
    loadMoreBtn.disabled = true;
  }
  
  try {
    const res = await fetch(`${API}/api/marketplace?init_data=${encodeURIComponent(tg.initData)}&sort=${sort}&offset=${currentMarketOffset}`);
    const d = await res.json();
    
    let html = '';
    if (d.length > 0) {
      html = '<div class="market-grid">' + d.map((l, i) => {
        const cls = l.is_premium ? 'premium' : l.is_auction ? 'auction' : '';
        const letter = l.username ? l.username[0].toUpperCase() : '?';
        const price = (l.current_bid || l.price).toLocaleString();
        const priceLabel = l.is_auction ? '⚡ Joriy stavka' : '💰 Narxi';
        const btnText = l.is_auction ? '⚡ Stavka berish' : '🛒 Sotib olish';
        const btnFn = l.is_auction ? `placeAuctionBid(${l.id}, ${l.current_bid || l.price})` : `buyListing(${l.id})`;
        const delay = (i % 4) * 60;
        return `
          <div class="market-card ${cls}" style="animation-delay:${delay}ms">
            ${l.is_premium ? '<div class="market-card-badge premium">👑 TOP</div>' : ''}
            ${l.is_auction ? '<div class="market-card-badge auction">⚡ AUKSION</div>' : ''}
            <div class="market-card-avatar ${cls}">${letter}</div>
            <div class="market-card-username ${cls}">@${l.username}</div>
            <div class="market-card-seller">${l.seller_name || 'Foydalanuvchi'}</div>
            <div class="market-card-price">
              <div class="market-card-price-label">${priceLabel}</div>
              <div class="market-card-price-value ${cls}">${price} so'm</div>
            </div>
            <button class="market-card-btn ${cls}" onclick="${btnFn}">${btnText}</button>
          </div>`;
      }).join('') + '</div>';
    }
    
    if (reset) {
      listEl.innerHTML = html || `<div style="text-align:center;padding:40px;color:var(--muted);">Sotuvda usernamelar yo'q</div>`;
    } else {
      const grid = listEl.querySelector('.market-grid');
      if (grid) grid.innerHTML += '<div class="market-grid" style="display:contents;">' + d.map((l, i) => {
        const cls = l.is_premium ? 'premium' : l.is_auction ? 'auction' : '';
        const letter = l.username ? l.username[0].toUpperCase() : '?';
        const price = (l.current_bid || l.price).toLocaleString();
        const priceLabel = l.is_auction ? '⚡ Joriy stavka' : '💰 Narxi';
        const btnText = l.is_auction ? '⚡ Stavka berish' : '🛒 Sotib olish';
        const btnFn = l.is_auction ? `placeAuctionBid(${l.id}, ${l.current_bid || l.price})` : `buyListing(${l.id})`;
        return `<div class="market-card ${cls}"><div class="market-card-avatar ${cls}">${letter}</div><div class="market-card-username ${cls}">@${l.username}</div><div class="market-card-seller">${l.seller_name || 'Foydalanuvchi'}</div><div class="market-card-price"><div class="market-card-price-label">${priceLabel}</div><div class="market-card-price-value ${cls}">${price} so'm</div></div><button class="market-card-btn ${cls}" onclick="${btnFn}">${btnText}</button></div>`;
      }).join('') + '</div>';
      else listEl.innerHTML += html;
    }
    
    if (d.length === 20) {
      currentMarketOffset += 20;
      loadMoreEl.style.display = 'block';
    } else {
      loadMoreEl.style.display = 'none';
    }
  } catch(e) {
    if (reset) listEl.innerHTML = 'Xato';
  } finally {
    loadMoreBtn.innerText = 'Yana yuklash';
    loadMoreBtn.disabled = false;
    filterMarket();
  }
}

async function loadMyListings() {
  document.getElementById('btn-market-all').className = 'btn btn-outline';
  document.getElementById('btn-market-my').className = 'btn btn-primary';
  document.getElementById('market-search').value = ''; // Tozalash
  document.getElementById('market-sort-container').style.display = 'none';
  document.getElementById('market-load-more').style.display = 'none';
  const listEl = document.getElementById('market-list');
  listEl.innerHTML = '<div style="text-align:center;padding:40px;"><div class="spinner" style="margin:0 auto 12px;"></div>Yuklanmoqda...</div>';
  try {
    const res = await fetch(`${API}/api/marketplace/my?init_data=${encodeURIComponent(tg.initData)}`);
    const d = await res.json();
    if (d.length > 0) {
      listEl.innerHTML = d.map(l => {
        const statTxt = {active:'Aktiv', sold:'Sotildi', cancelled:'Bekor qilingan'};
        return `
        <div class="order-item">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-weight:800; font-size:18px; color:var(--accent);">@${l.username}</div>
              <div style="font-size:12px; color:var(--muted); margin-top:4px;">Narxi: ${l.price.toLocaleString()} so'm</div>
            </div>
            <div style="text-align:right;">
              <div style="font-weight:700; font-size:14px; color:${l.status=='active'?'var(--success)':'var(--muted)'}">${statTxt[l.status]||l.status}</div>
              ${l.status == 'active' ? `<button class="btn btn-danger" style="padding:4px 8px; font-size:11px; margin:4px 0 0; width:auto;" onclick="cancelListing(${l.id})">O'chirish</button>` : ''}
            </div>
          </div>
        </div>
      `}).join('');
    } else {
      listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted);">Sizda e\'lonlar yo\'q</div>';
    }
  } catch(e) { listEl.innerHTML = 'Xato'; }
}

function filterMarket() {
  const query = document.getElementById('market-search').value.toLowerCase();
  // Support both old .order-item and new .market-card
  const items = document.querySelectorAll('#market-list .order-item, #market-list .market-card');
  items.forEach(item => {
    const text = item.innerText.toLowerCase();
    const isCard = item.classList.contains('market-card');
    item.style.display = text.includes(query) ? (isCard ? 'block' : 'block') : 'none';
  });
}

async function cancelListing(id) {
  if(!confirm("E'lonni o'chirasizmi? (E'lon puli qaytarilmaydi)")) return;
  try {
    const res = await fetch(`${API}/api/marketplace/cancel`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, listing_id: id})
    });
    const d = await res.json();
    if(d.ok) { showToast("O'chirildi", "success"); loadMyListings(); }
    else { showToast(d.error, "error"); }
  } catch(e) {}
}

async function openPostModal() {
  if(!userData.session_string) { showToast("Avval akkauntni ulang!", "error"); goPage("account"); return; }
  document.getElementById('market-post-modal').style.display = 'block';
  document.getElementById('market-overlay').style.display = 'block';
  const sel = document.getElementById('post-username-select');
  sel.innerHTML = '<option value="">Yuklanmoqda...</option>';
  try {
    const res = await fetch(`${API}/api/account/usernames?init_data=${encodeURIComponent(tg.initData)}`);
    const d = await res.json();
    if (d.usernames && d.usernames.length > 0) {
      sel.innerHTML = '<option value="">-- Tanlang --</option>' + d.usernames.map(u => 
        u.is_listed 
          ? `<option value="${u.username}" disabled>@${u.username} (Sotuvga qo'yilgan)</option>`
          : `<option value="${u.username}">@${u.username} (${u.title})</option>`
      ).join('');
    } else {
      sel.innerHTML = '<option value="">Sizda bo\'sh usernamelar yo\'q</option>';
    }
  } catch(e) { sel.innerHTML = '<option value="">Xato yuz berdi</option>'; }
}

function closeMarketPost() {
  document.getElementById('market-post-modal').style.display = 'none';
  if (document.getElementById('market-buy-modal').style.display === 'none') {
    document.getElementById('market-overlay').style.display = 'none';
  }
}

async function submitPostListing() {
  const username = document.getElementById('post-username-select').value;
  const price = parseInt(document.getElementById('post-price-input').value);
  const typeSelect = document.getElementById('post-type-select').value;
  const is_auction = typeSelect === 'auction' ? 1 : 0;
  
  if (!username) { showToast('Username tanlang!', 'error'); return; }
  if (!price || price < 1000) { showToast('Narxni to\'g\'ri kiriting (min 1,000)', 'error'); return; }
  
  let listingPriceStr = window.APP_PRICES ? window.APP_PRICES.listing.toLocaleString() : '1,000';
  let confirmMsg = is_auction 
    ? `Haqiqatdan ham @${username} ni ${price.toLocaleString()} so'm boshlang'ich narx bilan AUKSIONGA qo'yib, ${listingPriceStr} so'm to'lov yechishga rozimisiz?`
    : `Haqiqatdan ham @${username} ni ${price.toLocaleString()} so'mga sotuvga qo'yib, balansingizdan ${listingPriceStr} so'm e'lon to'lovini yechishga rozimisiz?`;
    
  if (!confirm(confirmMsg)) return;
  
  const btn = document.getElementById('btn-submit-post');
  btn.disabled = true;
  btn.innerText = 'Joylanmoqda...';
  try {
    const res = await fetch(`${API}/api/marketplace/list`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, username, price, is_auction})
    });
    const d = await res.json();
    if(d.ok) {
      showToast("E'lon qo'shildi!", "success");
      closeMarketPost();
      document.getElementById('post-price-input').value = '';
      loadUserData();
      loadMyListings();
    } else {
      showToast(d.error, "error");
    }
  } catch(e) { showToast("Xato yuz berdi", "error"); }
  btn.disabled = false;
  btn.innerText = 'Joylash';
}

async function buyListing(id) {
  try {
    const res = await fetch(`${API}/api/marketplace/buy`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, listing_id: id})
    });
    const d = await res.json();
    if(d.ok) {
      document.getElementById('market-buy-username').textContent = '@' + d.username;
      document.getElementById('market-buy-amount').textContent = d.amount.toLocaleString() + " so'm";
      document.getElementById('market-buy-card').textContent = d.card.slice(0,4)+' '+d.card.slice(4,8)+' '+d.card.slice(8,12)+' '+d.card.slice(12);
      document.getElementById('market-buy-modal').style.display = 'block';
      document.getElementById('market-overlay').style.display = 'block';
    } else {
      showToast(d.error, "error");
    }
  } catch(e) { showToast("Xato yuz berdi", "error"); }
}

function closeMarketBuy() {
  document.getElementById('market-buy-modal').style.display = 'none';
  document.getElementById('market-overlay').style.display = 'none';
}

async function loadCardNumber() {
  try {
    const res = await fetch(`${API}/api/card`);
    const d = await res.json();
    if (d.card) {
      const c = d.card;
      document.getElementById('card-number').textContent =
        c.slice(0,4)+' '+c.slice(4,8)+' '+c.slice(8,12)+' '+c.slice(12);
    }
  } catch(e) {}
}

async function loadOrders() {
  try {
    const res = await fetch(`${API}/api/orders?init_data=${encodeURIComponent(tg.initData)}`);
    const orders = await res.json();

    // Buyurtmalar sahifasi
    const el = document.getElementById('orders-list');
    if (el) {
      if (!orders.length) {
        el.innerHTML = `<div style="text-align:center;padding:40px;color:var(--muted);">
          <div style="font-size:48px;margin-bottom:12px;">📭</div>Buyurtmalar yo'q</div>`;
      } else {
        el.innerHTML = orders.map(o => {
          const statusMap = {pending:'badge-pending',processing:'badge-processing',completed:'badge-completed'};
          const statusTxt = {pending:'⏳ Kutilmoqda',processing:'🔄 Qidirilmoqda',completed:'✅ Bajarildi'};
          const chips = (o.usernames || []).map(u => `<span class="username-chip">@${u}</span>`).join('');
          return `<div class="order-item">
            <div class="order-top">
              <div class="order-cat">📂 ${o.category}</div>
              <span class="badge ${statusMap[o.status]||'badge-pending'}">${statusTxt[o.status]||o.status}</span>
            </div>
            <div class="order-meta">${o.registered_count}/${o.quantity} ta band • ${(o.price||0).toLocaleString()} so'm</div>
            ${chips ? `<div class="usernames-list">${chips}</div>` : ''}
          </div>`;
        }).join('');
      }
    }

    // Asosiy sahifadagi jadval
    const tbl = document.getElementById('home-orders-table');
    if (!orders.length) {
      tbl.innerHTML = `<div style="text-align:center;padding:24px;color:var(--muted);font-size:13px;">📭 Buyurtmalar yo'q</div>`;
    } else {
      const statusTxt = {pending:'⏳',processing:'🔄',completed:'✅'};
      tbl.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);">
            <th style="padding:10px 20px;text-align:left;color:var(--muted);font-weight:600;">Kalit so'z</th>
            <th style="padding:10px 8px;text-align:center;color:var(--muted);font-weight:600;">Band</th>
            <th style="padding:10px 20px 10px 8px;text-align:right;color:var(--muted);font-weight:600;">Holat</th>
          </tr>
        </thead>
        <tbody>${orders.slice(0,10).map((o,i) => `
          <tr style="border-bottom:${i<orders.length-1?'1px solid rgba(255,255,255,0.05)':'none'};">
            <td style="padding:12px 20px;font-weight:600;">📂 ${o.category}</td>
            <td style="padding:12px 8px;text-align:center;color:var(--accent2);">${o.registered_count}/${o.quantity}</td>
            <td style="padding:12px 20px 12px 8px;text-align:right;">${statusTxt[o.status]||'⏳'}</td>
          </tr>`).join('')}
        </tbody>
      </table>`;
    }
  } catch(e) { console.error(e); }
}

// ── NAVIGATION & LIQUID DRAG PHYSICS ────────────────
let currentDropletX = 0;
let isDraggingNav = false;

function moveDropletTo(navBtn, animate = true) {
  const droplet = document.getElementById('nav-droplet');
  if (!droplet || !navBtn) return;
  const navContainer = navBtn.parentElement;
  const btnRect = navBtn.getBoundingClientRect();
  const navRect = navContainer.getBoundingClientRect();
  
  const left = btnRect.left - navRect.left;
  const width = btnRect.width;
  currentDropletX = left;
  
  droplet.style.opacity = '1';
  droplet.style.setProperty('--snap-x', `${left}px`);
  
  if (animate) {
    droplet.classList.remove('dragging');
    droplet.style.transform = `translate(${left}px, -50%)`;
    droplet.style.width = `${width}px`;
    droplet.classList.remove('snap');
    void droplet.offsetWidth;
    droplet.classList.add('snap');
  } else {
    droplet.style.transform = `translate(${left}px, -50%)`;
    droplet.style.width = `${width}px`;
  }
}

// TOUCH / MOUSE DRAG LISTENERS FOR NAV
function initNavDragPhysics() {
  const navEl = document.querySelector('nav');
  const droplet = document.getElementById('nav-droplet');
  if (!navEl || !droplet) return;

  let startTouchX = 0;
  let initialLeft = 0;
  let lastX = 0;

  function onDragStart(clientX) {
    isDraggingNav = true;
    startTouchX = clientX;
    const activeBtn = document.querySelector('nav button.active');
    if (activeBtn) {
      const btnRect = activeBtn.getBoundingClientRect();
      const navRect = navEl.getBoundingClientRect();
      initialLeft = btnRect.left - navRect.left;
    }
    droplet.classList.add('dragging');
    droplet.classList.remove('snap');
  }

  function onDragMove(clientX) {
    if (!isDraggingNav) return;
    const deltaX = clientX - startTouchX;
    const navRect = navEl.getBoundingClientRect();
    const maxLeft = navRect.width - 65;
    let targetX = Math.max(0, Math.min(maxLeft, initialLeft + deltaX));
    
    // Calculate speed for liquid stretch physics
    const speed = clientX - lastX;
    lastX = clientX;
    const stretch = Math.min(20, Math.abs(speed) * 1.2);
    
    droplet.style.transform = `translate(${targetX}px, -50%) scaleX(${1 + stretch/60}) scaleY(${1 - stretch/100})`;
    
    // Highlight nearest button while dragging
    const buttons = Array.from(document.querySelectorAll('nav button'));
    let closestBtn = null;
    let minDist = Infinity;
    
    buttons.forEach(btn => {
      const bRect = btn.getBoundingClientRect();
      const center = bRect.left - navRect.left + bRect.width / 2;
      const dist = Math.abs(center - (targetX + 32));
      if (dist < minDist) {
        minDist = dist;
        closestBtn = btn;
      }
    });

    if (closestBtn && !closestBtn.classList.contains('active')) {
      buttons.forEach(b => b.classList.remove('active'));
      closestBtn.classList.add('active');
    }
  }

  function onDragEnd() {
    if (!isDraggingNav) return;
    isDraggingNav = false;
    droplet.classList.remove('dragging');
    
    const activeBtn = document.querySelector('nav button.active');
    if (activeBtn) {
      const pageId = activeBtn.id.replace('nav-', '');
      goPage(pageId);
    }
  }

  navEl.addEventListener('touchstart', (e) => onDragStart(e.touches[0].clientX), {passive: true});
  navEl.addEventListener('touchmove', (e) => onDragMove(e.touches[0].clientX), {passive: true});
  navEl.addEventListener('touchend', onDragEnd);
  navEl.addEventListener('mousedown', (e) => onDragStart(e.clientX));
  window.addEventListener('mousemove', (e) => isDraggingNav && onDragMove(e.clientX));
  window.addEventListener('mouseup', onDragEnd);
}

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(initNavDragPhysics, 300);
});

function goPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  const pageEl = document.getElementById('page-'+name);
  if (!pageEl) { name = 'home'; document.getElementById('page-home').classList.add('active'); }
  else { pageEl.classList.add('active'); }
  const navBtn = document.getElementById('nav-'+name);
  if (navBtn) {
    navBtn.classList.add('active');
    moveDropletTo(navBtn);
  }
  if(name==='monitor') loadMonitors();
  if(name==='market') loadMarketplace();
  if(name==='my-listings') loadMyListings();
  if(name==='balance'||name==='home') { loadUserData(); loadOrders(); }
}

window.addEventListener('resize', () => {
  const activeBtn = document.querySelector('nav button.active');
  if (activeBtn) moveDropletTo(activeBtn);
});
setTimeout(() => {
  const activeBtn = document.querySelector('nav button.active');
  if (activeBtn) moveDropletTo(activeBtn);
}, 100);

// ── MONITORING LOGIC ──────────────────────────
async function startMonitor() {
  const username = document.getElementById('monitor-username').value.trim();
  if (!username) { showToast('Username kiriting!','error'); return; }
  if (!userData.session_string) { showToast('Avval akkauntni ulang!','error'); goPage('account'); return; }
  
  const monitorPrice = window.APP_PRICES ? window.APP_PRICES.monitor : 10000;
  if ((userData.balance||0) < monitorPrice) {
    showToast(`Balans yetarli emas (${monitorPrice.toLocaleString()} UZS)`,'error');
    return;
  }
  
  try {
    const res = await fetch(`${API}/api/monitor/start`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, username: username})
    });
    const d = await res.json();
    if (d.ok) {
      showToast('✅ Kuzatuv boshlandi!','success');
      document.getElementById('monitor-username').value = '';
      await loadUserData();
      await loadMonitors();
    } else { showToast(d.error||'Xato yuz berdi','error'); }
  } catch(e) { showToast('Tarmoq xatosi','error'); }
}

async function loadMonitors() {
  try {
    const res = await fetch(`${API}/api/monitor/list?init_data=${encodeURIComponent(tg.initData)}`);
    const d = await res.json();
    if(!d.ok) return;
    
    const el = document.getElementById('monitor-list');
    if (!d.tasks || !d.tasks.length) {
      el.innerHTML = `<div style="text-align:center;padding:24px;color:var(--muted);font-size:13px;">📭 Hozircha nishonlar yo'q</div>`;
    } else {
      const stMap = {
        'monitoring': '<span style="color:var(--warning);">🔍 Kuzatilmoqda</span>',
        'claimed': '<span style="color:var(--success);">✅ Olingan!</span>',
        'failed_limit': '<span style="color:var(--danger);">❌ Limit tugagan</span>'
      };
      
      el.innerHTML = d.tasks.map(t => `
        <div style="padding:12px 20px; border-bottom:1px solid rgba(255,255,255,0.05); display:flex; justify-content:space-between; align-items:center;">
          <div style="font-weight:600;">@${t.username}</div>
          <div style="font-size:12px;">${stMap[t.status] || t.status}</div>
        </div>
      `).join('');
    }
  } catch(e) {}
}

// ── INTERACTIVE SEARCH & BUY ──────────────────
let currentSearchId = null;
let paidQty = 0;           // Oldindan to'langan miqdor
let searchPollInterval = null;
let selectedUsernames = new Set();
const PRICE_PER_ITEM = 5000;

function calcSearchPrice() {
  const qty = Math.min(10, Math.max(1, parseInt(document.getElementById('buy-qty').value) || 1));
  const free = userData.free_searches || 0;
  const priceQty = Math.max(0, qty - free);
  const total = priceQty * PRICE_PER_ITEM;
  
  let labelText = total.toLocaleString() + " so'm";
  if (free > 0) {
    labelText += ` <span style="font-size:12px; color:var(--success); font-weight:normal;">(${Math.min(qty, free)} ta bepul)</span>`;
  }
  document.getElementById('search-total-price').innerHTML = labelText;
  
  const warn = document.getElementById('search-balance-warn');
  warn.style.display = (userData.balance || 0) < total ? 'block' : 'none';
}

async function startSearch() {
  let cat = document.getElementById('buy-category').value.trim();
  if (cat === 'custom') {
    const word = document.getElementById('buy-custom-word').value.trim();
    if (!word || word.length < 2) {
      showToast("Iltimos, eng kamida 2 ta harfdan iborat so'z kiriting!", "error");
      return;
    }
    cat = "custom:" + word;
  }
  const lang = document.getElementById('buy-lang').value;
  const qty = Math.min(10, Math.max(1, parseInt(document.getElementById('buy-qty').value) || 1));
  if (!cat) { showToast('Kategoriya kiriting!','error'); return; }
  if (!userData.session_string) { showToast('Avval akkauntni ulang!','error'); goPage('account'); return; }

  const free = userData.free_searches || 0;
  const priceQty = Math.max(0, qty - free);
  const totalPrice = priceQty * PRICE_PER_ITEM;

  if ((userData.balance || 0) < totalPrice) {
    showToast('Balans yetarli emas!', 'error');
    goPage('balance');
    return;
  }

  const btn = document.getElementById('search-btn');
  btn.innerHTML = '<div class="spinner"></div> To\'lanmoqda...';
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/api/search/start`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, category: cat, quantity: qty, lang: lang})
    });
    const d = await res.json();
    if (d.ok) {
      paidQty = qty;
      currentSearchId = d.search_id;
      await loadUserData(); // Balansni yangilash

      document.getElementById('search-results-card').style.display = 'block';
      document.getElementById('results-list').innerHTML = '';
      document.getElementById('paid-count').textContent = paidQty;
      document.getElementById('search-must-select-hint').innerHTML =
        `Siz <b>${paidQty} ta</b> username uchun to'ladingiz. Xuddi shuncha tanlashingiz kerak!`;
      selectedUsernames.clear();
      updateSelectionUI();

      if(searchPollInterval) clearInterval(searchPollInterval);
      searchPollInterval = setInterval(pollSearchResults, 2000);
      if (totalPrice > 0) {
        showToast(`✅ ${totalPrice.toLocaleString()} so'm yechildi!`, 'success');
      } else {
        showToast(`✅ Bepul qidiruv ishga tushdi!`, 'success');
      }
    } else {
      showToast(d.error || 'Xato yuz berdi', 'error');
    }
  } catch(e) {
    showToast('Xato yuz berdi', 'error');
    console.error(e);
  } finally {
    btn.innerHTML = '💳 To\'lab qidirish';
    btn.disabled = false;
  }
}

async function pollSearchResults() {
  if(!currentSearchId) return;
  try {
    const res = await fetch(`${API}/api/search/results?search_id=${currentSearchId}&init_data=${encodeURIComponent(tg.initData)}`);
    const d = await res.json();
    if(d.ok) {
      if(d.status === 'completed') {
        clearInterval(searchPollInterval);
        document.getElementById('search-status-text').innerHTML = '✅ Qidiruv yakunlandi.';
      } else if(d.status && d.status.startsWith('error_floodwait')) {
        clearInterval(searchPollInterval);
        let msg = "⚠️ Telegram cheklovi: Birozdan so'ng qayta urinib ko'ring (FloodWait).";
        const parts = d.status.split(':');
        if (parts.length > 1) {
            const secs = parseInt(parts[1], 10);
            let timeStr = "";
            if (secs >= 3600) {
                timeStr = Math.floor(secs / 3600) + " soat " + Math.floor((secs % 3600)/60) + " daqiqa";
            } else if (secs >= 60) {
                timeStr = Math.floor(secs / 60) + " daqiqa";
            } else {
                timeStr = secs + " soniya";
            }
            msg = `⚠️ Telegram cheklovi: Akkaunt blokdan chiqishi uchun <b>${timeStr}</b> kutishingiz kerak.`;
        }
        document.getElementById('search-status-text').innerHTML = msg;
      }
      renderSearchResults(d.results);
    }
  } catch(e) {}
}

// Username carousel state
let currentResultIndex = 0;
let cachedFreeResults = [];

function renderSearchResults(results) {
  const list = document.getElementById('results-list');
  cachedFreeResults = results.filter(r => r.status !== 'claimed');
  
  if(cachedFreeResults.length === 0) {
    list.innerHTML = `<div style="padding:16px; text-align:center; color:var(--muted);">Hozircha natija yo'q...</div>`;
    updateSelectionUI();
    return;
  }
  
  // Ensure current index stays in bounds
  if(currentResultIndex >= cachedFreeResults.length) currentResultIndex = 0;
  renderCarousel();
}

function renderCarousel() {
  const list = document.getElementById('results-list');
  const results = cachedFreeResults;
  if(results.length === 0) return;
  
  const r = results[currentResultIndex];
  const total = results.length;
  const isChecked = selectedUsernames.has(r.username);
  const isMaxReached = selectedUsernames.size >= paidQty && !selectedUsernames.has(r.username);
  const disabled = isMaxReached;
  
  const prevDisabled = currentResultIndex === 0;
  const nextDisabled = currentResultIndex === total - 1;
  
  list.innerHTML = `
    <div style="padding:8px 14px 4px; display:flex; align-items:center; justify-content:space-between;">
      <span style="font-size:12px; color:var(--muted)">${currentResultIndex+1} / ${total} ta topildi</span>
      <span style="font-size:12px; color:var(--muted)">${selectedUsernames.size}/${paidQty} tanlangan</span>
    </div>
    
    <div style="display:flex; align-items:center; padding:16px 12px; gap:10px;">
      <button onclick="carouselPrev()" ${prevDisabled ? 'disabled' : ''}
        style="width:38px; height:38px; border-radius:50%; border:none; background:rgba(255,255,255,0.1); color:white; font-size:18px; cursor:${prevDisabled?'not-allowed':'pointer'}; opacity:${prevDisabled?'0.3':'1'}; flex-shrink:0; transition:all .2s;">
        ◀
      </button>
      
      <label style="flex:1; display:flex; align-items:center; padding:14px 16px; border-radius:12px; background:rgba(255,255,255,0.05); border:2px solid ${isChecked ? 'var(--primary)' : 'rgba(255,255,255,0.1)'}; cursor:${disabled?'not-allowed':'pointer'}; opacity:${disabled?'0.5':'1'}; transition:all .2s;">
        <input type="checkbox" value="${r.username}" onchange="toggleSelection(this)" ${isChecked ? 'checked' : ''} ${disabled ? 'disabled' : ''}
          style="width:20px; height:20px; accent-color:var(--primary); flex-shrink:0; margin-right:12px;">
        <div>
          <div style="font-weight:700; font-size:16px;">@${r.username}</div>
          <div style="font-size:12px; color:var(--muted); margin-top:2px;">${isChecked ? '✅ Tanlangan' : (disabled ? '🔒 Limit to\'ldi' : '⬜ Tanlash uchun bosing')}</div>
        </div>
      </label>
      
      <button onclick="carouselNext()" ${nextDisabled ? 'disabled' : ''}
        style="width:38px; height:38px; border-radius:50%; border:none; background:rgba(255,255,255,0.1); color:white; font-size:18px; cursor:${nextDisabled?'not-allowed':'pointer'}; opacity:${nextDisabled?'0.3':'1'}; flex-shrink:0; transition:all .2s;">
        ▶
      </button>
    </div>
    
    <div style="display:flex; justify-content:center; gap:6px; padding:4px 14px 10px;">
      ${results.map((_, i) => `<div onclick="carouselGoto(${i})" style="width:${i===currentResultIndex?'20px':'8px'}; height:8px; border-radius:4px; background:${i===currentResultIndex?'var(--primary)':'rgba(255,255,255,0.2)'}; cursor:pointer; transition:all .3s;"></div>`).join('')}
    </div>
  `;
}

function carouselPrev() {
  if(currentResultIndex > 0) { currentResultIndex--; renderCarousel(); }
}
function carouselNext() {
  if(currentResultIndex < cachedFreeResults.length - 1) { currentResultIndex++; renderCarousel(); }
}
function carouselGoto(idx) {
  currentResultIndex = idx;
  renderCarousel();
}


async function nextSearch() {
  if (!currentSearchId) return;
  const btn = document.getElementById('next-search-btn');
  btn.innerHTML = '<div class="spinner" style="display:inline-block;width:16px;height:16px;"></div> Qidirilmoqda...';
  btn.disabled = true;

  // Joriy qidiruvning kategoriyasini olamiz
  let cat = document.getElementById('buy-category').value.trim();
  if (cat === 'custom') {
    const word = document.getElementById('buy-custom-word').value.trim();
    if (!word || word.length < 2) {
      btn.innerHTML = '➡️ Keyingi (yangi variantlar ko\'rsatish)';
      btn.disabled = false;
      return;
    }
    cat = "custom:" + word;
  }
  if (!cat) { btn.innerHTML = '➡️ Keyingi'; btn.disabled = false; return; }

  try {
    // Yangi search_task yaratamiz, lekin pul yechilmaydi (refresh)
    const res = await fetch(`${API}/api/search/refresh`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, category: cat, paid_qty: paidQty})
    });
    const d = await res.json();
    if (d.ok) {
      currentSearchId = d.search_id;
      document.getElementById('results-list').innerHTML = '';
      document.getElementById('search-status-text').textContent = '⏳ Yangi variantlar qidirilmoqda...';
      selectedUsernames.clear();
      updateSelectionUI();

      if(searchPollInterval) clearInterval(searchPollInterval);
      searchPollInterval = setInterval(pollSearchResults, 2000);
    } else {
      showToast(d.error || 'Xato', 'error');
    }
  } catch(e) { showToast('Tarmoq xatosi', 'error'); }

  btn.innerHTML = '➡️ Keyingi (yangi variantlar ko\'rsatish)';
  btn.disabled = false;
}

function toggleSelection(checkbox) {
  if(checkbox.checked) {
    if(selectedUsernames.size >= paidQty) {
      showToast(`Siz faqat ${paidQty} ta tanlay olasiz!`, 'error');
      checkbox.checked = false;
      return;
    }
    selectedUsernames.add(checkbox.value);
  } else {
    selectedUsernames.delete(checkbox.value);
  }
  updateSelectionUI();
  // Carousel kartani yangilash (belgi va rangni ko'rsatish)
  if(cachedFreeResults.length > 0) renderCarousel();
  // Tanlangandan so'ng keyingi username ga o'tish
  if(checkbox.checked && currentResultIndex < cachedFreeResults.length - 1) {
    setTimeout(() => { currentResultIndex++; renderCarousel(); }, 400);
  }
}

function updateSelectionUI() {
  const count = selectedUsernames.size;
  document.getElementById('selected-count').textContent = count;

  const buyBtn = document.getElementById('buy-btn');
  // Foydalanuvchi to'lagan miqdorcha tanlasa aktiv bo'ladi
  if (count > 0 && count === paidQty) {
    buyBtn.disabled = false;
    buyBtn.innerHTML = `✅ ${count} ta nomni band qilish`;
  } else if (count > 0) {
    buyBtn.disabled = true;
    buyBtn.innerHTML = `✅ Yana ${paidQty - count} ta tanlang...`;
  } else {
    buyBtn.disabled = true;
    buyBtn.innerHTML = `✅ Tanlanganlarni band qilish`;
  }
}

async function buySelected() {
  const usernames = Array.from(selectedUsernames);
  if(!usernames.length) return;
  
  const btn = document.getElementById('buy-btn');
  btn.innerHTML = '<div class="spinner"></div> Band qilinmoqda...';
  btn.disabled = true;
  
  try {
    const res = await fetch(`${API}/api/buy_selected`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, search_id: currentSearchId, usernames: usernames})
    });
    const d = await res.json();
    if(d.ok) {
      showToast('✅ Tanlanganlar band qilinmoqda!','success');
      selectedUsernames.clear();
      updateSelectionUI();
      await loadUserData();
      // Yana natijalarni yangilaymiz (statusi claimed bo'lishi uchun)
      pollSearchResults();
      goPage('home');
    } else {
      showToast(d.error||'Xato','error');
      btn.disabled = false;
    }
  } catch(e) {
    showToast('Xato yuz berdi','error');
    btn.disabled = false;
  }
  btn.innerHTML = '✅ Tanlanganlarni band qilish';
}

// ── TOPUP ───────────────────────────────────
let topupTimerInterval = null;

async function requestTopup() {
  const amtInput = document.getElementById('topup-amount').value;
  const amt = parseInt(amtInput);
  if (!amt || amt < 15000) { showToast('Kamida 15,000 so\'m kiriting', 'error'); return; }
  
  try {
    const res = await fetch(`${API}/api/topup/request`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, amount: amt})
    });
    const d = await res.json();
    if (d.ok) {
      document.getElementById('topup-form-wrap').style.display = 'none';
      document.getElementById('topup-pay-wrap').style.display = 'block';
      document.getElementById('pay-exact-amount').textContent = d.amount.toLocaleString() + ' so\'m';
      
      // Timer mantiqi
      let timeLeft = d.expires_in || 180;
      const timerEl = document.getElementById('topup-timer');
      if(topupTimerInterval) clearInterval(topupTimerInterval);
      
      const updateTimerDisplay = () => {
        const m = Math.floor(timeLeft / 60).toString().padStart(2, '0');
        const s = (timeLeft % 60).toString().padStart(2, '0');
        timerEl.textContent = `${m}:${s}`;
      };
      updateTimerDisplay();
      
      topupTimerInterval = setInterval(() => {
        timeLeft--;
        if(timeLeft <= 0) {
          clearInterval(topupTimerInterval);
          showToast('⏳ 3 daqiqalik to\'lov vaqti tugadi!', 'error');
          alert("⏳ 3 daqiqalik to'lov vaqti tugadi!\n\nAgar to'lovni o'tkazgan bo'lsangiz xavotir olmang, balans avtomatik to'ldiriladi. Lekin yangi to'lov uchun yangidan summa kiritishingiz so'raladi.");
          cancelTopup();
        } else {
          updateTimerDisplay();
        }
      }, 1000);
      
    } else { showToast(d.error||'Xato','error'); }
  } catch(e) { showToast('Tarmoq xatosi','error'); }
}

function cancelTopup() {
  if(topupTimerInterval) clearInterval(topupTimerInterval);
  document.getElementById('topup-form-wrap').style.display = 'block';
  document.getElementById('topup-pay-wrap').style.display = 'none';
  document.getElementById('topup-amount').value = '';
}

function copyCard() {
  const txt = document.getElementById('card-number').textContent.replace(/\s/g,'');
  navigator.clipboard?.writeText(txt);
  showToast('📋 Nusxalandi!','success');
}

// ── TELEGRAM AUTH ─────────────────────────────
async function sendAuthCode() {
  const phone = document.getElementById('auth-phone').value.trim();
  if (!phone) { showToast('Telefon kiritilmadi', 'error'); return; }
  const btn = document.getElementById('btn-send-code');
  btn.innerText = 'Yuborilmoqda...'; btn.disabled = true;
  try {
    const res = await fetch(`${API}/api/auth/send_code`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, phone: phone})
    });
    const d = await res.json();
    if (d.ok) {
      document.getElementById('auth-step-phone').style.display = 'none';
      document.getElementById('auth-step-code').style.display = 'block';
      showToast('Kod yuborildi!', 'success');
    } else { showToast(d.error||'Xato', 'error'); }
  } catch(e) { showToast('Xato yuz berdi', 'error'); }
  btn.innerText = 'Kod yuborish'; btn.disabled = false;
}

async function verifyAuthCode() {
  const code = document.getElementById('auth-code').value.trim();
  if (!code) { showToast('Kodni kiriting', 'error'); return; }
  const btn = document.getElementById('btn-verify-code');
  btn.innerText = 'Tekshirilmoqda...'; btn.disabled = true;
  try {
    const res = await fetch(`${API}/api/auth/login`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, code: code})
    });
    const d = await res.json();
    if (d.ok) {
      if (d.need_password) {
        document.getElementById('auth-step-code').style.display = 'none';
        document.getElementById('auth-step-password').style.display = 'block';
      } else {
        showToast('✅ Akkaunt ulandi!', 'success');
        await loadUserData();
      }
    } else { showToast(d.error||'Noto\'g\'ri kod', 'error'); }
  } catch(e) { showToast('Xato yuz berdi', 'error'); }
  btn.innerText = 'Tasdiqlash'; btn.disabled = false;
}

async function verifyAuthPassword() {
  const pwd = document.getElementById('auth-password').value.trim();
  if (!pwd) { showToast('Parolni kiriting', 'error'); return; }
  const btn = document.getElementById('btn-verify-pass');
  btn.innerText = 'Tekshirilmoqda...'; btn.disabled = true;
  try {
    const res = await fetch(`${API}/api/auth/password`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, password: pwd})
    });
    const d = await res.json();
    if (d.ok) {
      showToast('✅ Akkaunt ulandi!', 'success');
      await loadUserData();
    } else { showToast(d.error||'Noto\'g\'ri parol', 'error'); }
  } catch(e) { showToast('Xato yuz berdi', 'error'); }
  btn.innerText = 'Kirish'; btn.disabled = false;
}

async function disconnectAccount() {
  if (!confirm('Akkauntni uzishni tasdiqlaysizmi?')) return;
  try {
    await fetch(`${API}/api/session/disconnect`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData})
    });
    showToast('Akkaunt uzildi','success');
    userData.session_string = null;
    document.getElementById('status-dot').className = 'status-dot disconnected';
    document.getElementById('account-name').textContent = 'Akkaunt ulanmagan';
    document.getElementById('session-form-wrap').style.display = 'block';
    document.getElementById('auth-step-phone').style.display = 'block';
    document.getElementById('auth-step-code').style.display = 'none';
    document.getElementById('auth-step-password').style.display = 'none';
    document.getElementById('disconnect-wrap').style.display = 'none';
  } catch(e) {}
}

// ── TOAST ─────────────────────────────────────
function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ── PREMIUM & SUBSCRIPTIONS ───────────────────
async function buyPremium() {
  const premiumPriceStr = window.APP_PRICES ? window.APP_PRICES.premium.toLocaleString() : '20,000';
  if(!confirm(`${premiumPriceStr} so'm evaziga 30 kunga Premium sotib olasizmi?`)) return;
  const btn = document.getElementById('btn-buy-premium');
  btn.disabled = true; btn.innerText = 'Kuting...';
  try {
    const res = await fetch(`${API}/api/premium/buy`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData})
    });
    const d = await res.json();
    if(d.ok) {
      showToast('Premium faollashtirildi!', 'success');
      loadUserData();
    } else {
      showToast(d.error, 'error');
    }
  } catch(e) { showToast('Xato', 'error'); }
  btn.disabled = false; btn.innerText = 'Sotib olish';
}

async function loadSubscriptions() {
  try {
    const res = await fetch(`${API}/api/subscriptions?init_data=${encodeURIComponent(tg.initData)}`);
    const d = await res.json();
    const listEl = document.getElementById('sub-keyword-list');
    listEl.innerHTML = d.map(s => `
      <div style="background:var(--accent); color:#fff; padding:6px 12px; border-radius:16px; font-size:12px; display:flex; align-items:center; gap:6px;">
        ${s.keyword}
        <span style="cursor:pointer; font-weight:bold; background:rgba(0,0,0,0.2); border-radius:50%; width:18px; height:18px; display:inline-flex; align-items:center; justify-content:center;" onclick="removeSubKeyword(${s.id})">×</span>
      </div>
    `).join('');
  } catch(e) {}
}

async function addSubKeyword() {
  const kw = document.getElementById('sub-keyword-input').value.trim();
  if(kw.length < 3) { showToast('Kamida 3 ta harf', 'error'); return; }
  try {
    const res = await fetch(`${API}/api/subscriptions/add`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, keyword: kw})
    });
    const d = await res.json();
    if(d.ok) {
      document.getElementById('sub-keyword-input').value = '';
      loadSubscriptions();
    } else { showToast(d.error, 'error'); }
  } catch(e) { showToast('Xato', 'error'); }
}

async function removeSubKeyword(id) {
  try {
    await fetch(`${API}/api/subscriptions/remove`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({init_data: tg.initData, id: id})
    });
    loadSubscriptions();
  } catch(e) {}
}

function copyEscrowLink(id, username) {
  const link = `https://t.me/usernamechi_bot?start=escrow_${id}`;
  navigator.clipboard.writeText(link).then(() => {
    showToast('Havola nusxalandi!', 'success');
  }).catch(() => {
    showToast('Nusxalashda xatolik', 'error');
  });
}

init();

// Twemoji — barcha emoji'larni yuqori sifatli vektor SVG rasmga aylantiradi (100% har qanday qurilmada ishlaydi)
if (typeof twemoji !== 'undefined') {
  twemoji.parse(document.body, {
    folder: 'svg',
    ext: '.svg',
    base: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/'
  });
}
