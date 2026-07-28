import re

def inject_frontend():
    with open('static/app/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    css_inject = """
    <style>
      /* --- Force Subscription Modal (Telegram Premium Style) --- */
      #force-sub-overlay {
        position: fixed; top:0; left:0; width:100%; height:100%;
        background: rgba(0,0,0,0.6); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
        z-index: 999999; display: none; align-items: center; justify-content: center;
        opacity: 0; transition: opacity 0.3s ease;
      }
      #force-sub-overlay.show { opacity: 1; }
      
      .force-sub-modal {
        width: 90%; max-width: 360px;
        background: linear-gradient(145deg, rgba(30,41,59,0.95) 0%, rgba(15,23,42,0.98) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 24px; padding: 24px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5), inset 0 1px 1px rgba(255,255,255,0.1);
        transform: translateY(20px) scale(0.95); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        text-align: center; color: #fff; position: relative; overflow: hidden;
      }
      #force-sub-overlay.show .force-sub-modal { transform: translateY(0) scale(1); }
      
      /* Premium Glow Effect */
      .force-sub-modal::before {
        content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 50%);
        animation: rotateGlow 10s linear infinite; pointer-events: none;
      }
      @keyframes rotateGlow { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

      .force-sub-icon {
        width: 64px; height: 64px; margin: 0 auto 16px auto;
        background: linear-gradient(135deg, #8b5cf6, #3b82f6);
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 28px; box-shadow: 0 8px 16px rgba(139,92,246,0.3);
      }
      
      .force-sub-title { font-size: 20px; font-weight: 800; margin-bottom: 8px; font-family: 'Inter', sans-serif; }
      .force-sub-desc { font-size: 14px; color: #94a3b8; margin-bottom: 24px; line-height: 1.4; }
      
      .force-sub-list {
        display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px; max-height: 200px; overflow-y: auto;
      }
      .force-sub-channel-btn {
        display: flex; align-items: center; justify-content: space-between;
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px; padding: 12px 16px; text-decoration: none; color: #fff;
        transition: all 0.2s ease;
      }
      .force-sub-channel-btn:active { background: rgba(255,255,255,0.1); transform: scale(0.98); }
      .force-sub-channel-name { font-weight: 600; font-size: 15px; display:flex; align-items:center; gap:8px; }
      .force-sub-channel-icon { font-size: 18px; }
      
      .force-sub-check-btn {
        width: 100%; padding: 14px; border-radius: 14px; border: none;
        background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff;
        font-size: 16px; font-weight: 700; cursor: pointer;
        box-shadow: 0 4px 12px rgba(59,130,246,0.4); transition: all 0.2s ease;
        position: relative; overflow: hidden;
      }
      .force-sub-check-btn:active { transform: scale(0.97); }
      
      /* Loader */
      .force-sub-loader { display: none; width: 20px; height: 20px; border: 3px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; }
      @keyframes spin { to { transform: rotate(360deg); } }
    </style>
"""
    if "/* --- Force Subscription Modal" not in content:
        content = content.replace("</head>", css_inject + "</head>")

    html_inject = """
  <!-- FORCE SUBSCRIPTION MODAL -->
  <div id="force-sub-overlay">
    <div class="force-sub-modal">
      <div class="force-sub-icon">🚀</div>
      <div class="force-sub-title">Xush kelibsiz!</div>
      <div class="force-sub-desc">Botdan to'liq foydalanish va barcha imkoniyatlarni ochish uchun quyidagi homiy kanallariga a'zo bo'ling.</div>
      
      <div class="force-sub-list" id="force-sub-channels">
        <!-- Channels injected here -->
      </div>
      
      <button class="force-sub-check-btn" id="force-sub-check-btn" onclick="checkForceSubscription()">
        <span id="force-sub-check-text">✅ Tekshirish</span>
        <div id="force-sub-check-loader" class="force-sub-loader"></div>
      </button>
    </div>
  </div>
"""
    if "<!-- FORCE SUBSCRIPTION MODAL -->" not in content:
        content = content.replace("<body>", "<body>\n" + html_inject)

    js_inject = """
    // --- GLOBAL FETCH INTERCEPTOR FOR FORCE SUBSCRIPTION ---
    const originalFetch = window.fetch;
    window.fetch = async function() {
      let [resource, config] = arguments;
      if (!config) config = {};
      if (!config.headers) config.headers = {};
      
      // Inject Header directly if initData exists
      if (tg && tg.initData) {
        config.headers['X-Telegram-Init-Data'] = tg.initData;
      }
      
      const response = await originalFetch(resource, config);
      
      // Catch 403 Subscription Required globally
      if (response.status === 403) {
        const cloned = response.clone();
        try {
          const data = await cloned.json();
          if (data.error === 'subscription_required' && data.channels) {
            showForceSubModal(data.channels);
            // Block the promise chain to prevent other errors
            return new Promise(() => {});
          }
        } catch(e) {}
      }
      return response;
    };

    function showForceSubModal(channels) {
      if(tg && tg.expand) tg.expand();
      const listEl = document.getElementById('force-sub-channels');
      listEl.innerHTML = channels.map(ch => {
        const link = ch.url || (ch.channel_username ? 'https://t.me/'+ch.channel_username : '#');
        return `
          <a href="${link}" target="_blank" class="force-sub-channel-btn">
            <span class="force-sub-channel-name"><span class="force-sub-channel-icon">📢</span> ${ch.title}</span>
            <span style="font-size:12px; background:rgba(255,255,255,0.1); padding:4px 8px; border-radius:8px;">A'zo bo'lish</span>
          </a>
        `;
      }).join('');
      
      const overlay = document.getElementById('force-sub-overlay');
      overlay.style.display = 'flex';
      setTimeout(() => overlay.classList.add('show'), 10);
    }

    async function checkForceSubscription() {
      const btnText = document.getElementById('force-sub-check-text');
      const loader = document.getElementById('force-sub-check-loader');
      btnText.style.display = 'none';
      loader.style.display = 'block';
      
      try {
        const res = await originalFetch(`${API}/api/check_subscription`, {
          method: 'GET',
          headers: { 'X-Telegram-Init-Data': tg.initData }
        });
        const data = await res.json();
        if (data.ok) {
          // Success! Hide modal and reload the current app logic
          const overlay = document.getElementById('force-sub-overlay');
          overlay.classList.remove('show');
          setTimeout(() => {
            overlay.style.display = 'none';
            // Reload user data or page smoothly
            if (typeof loadUserData === 'function') loadUserData();
            else window.location.reload();
          }, 300);
          if(tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } else {
          // Update channels list
          if (data.channels) showForceSubModal(data.channels);
          if(tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
          showToast("Iltimos, barcha kanallarga a'zo bo'ling", "error");
        }
      } catch (e) {
        showToast("Tarmoq xatosi", "error");
      } finally {
        btnText.style.display = 'block';
        loader.style.display = 'none';
      }
    }
"""
    if "GLOBAL FETCH INTERCEPTOR" not in content:
        idx = content.find("<script>")
        if idx != -1:
            idx = content.find("</script>", idx)
            content = content[:idx] + js_inject + "\n" + content[idx:]

    with open('static/app/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Injected frontend interceptor and modal.")

if __name__ == "__main__":
    inject_frontend()
