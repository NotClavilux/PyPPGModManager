// ==UserScript==
// @name         GOG Mod Manager Helper
// @namespace    http://tampermonkey.net/
// @version      2.0.0
// @description  Install, update, delete, and manage mods for People Playground and Project Zomboid.
// @author       notclavilux
// @match        https://steamcommunity.com/sharedfiles/filedetails/?id=*
// @match        https://steamcommunity.com/workshop/browse*appids=1118200*
// @match        https://steamcommunity.com/app/1118200/workshop*
// @match        https://steamcommunity.com/workshop/browse*appids=108600*
// @match        https://steamcommunity.com/app/108600/workshop*
// @connect      localhost
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const BACKEND_URL = 'http://localhost:8000';
    const DEFAULT_REQUEST_TIMEOUT = 30000;
    const INSTALL_REQUEST_TIMEOUT = 300000;

    GM_addStyle(`
        .gmm-button-container { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
        .gmm-action-button, .gmm-global-button {
            border: none; color: white; padding: 10px 20px; text-align: center;
            text-decoration: none; display: block; font-size: 14px;
            cursor: pointer; border-radius: 4px; width: 100%;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: background-color 0.2s ease, box-shadow 0.2s ease;
            box-sizing: border-box;
        }
        .gmm-action-button:hover, .gmm-global-button:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.3); }
        .gmm-action-button.install { background-color: #4CAF50; }
        .gmm-action-button.install:hover { background-color: #45a049; }
        .gmm-action-button.delete { background-color: #f44336; }
        .gmm-action-button.delete:hover { background-color: #da190b; }
        .gmm-action-button.update { background-color: #007bff; }
        .gmm-action-button.update:hover { background-color: #0056b3; }
        .gmm-action-button.disable { background-color: #ffc107; color: black; }
        .gmm-action-button.disable:hover { background-color: #e0a800; }
        .gmm-action-button.enable { background-color: #28a745; }
        .gmm-action-button.enable:hover { background-color: #218838; }
        .gmm-action-button.loading, .gmm-global-button.loading { background-color: #757575; cursor: not-allowed; }
        .gmm-global-button { position: fixed; bottom: 15px; right: 15px; z-index: 9999; width: auto; padding: 10px 15px; background-color: #343a40; }
        .gmm-global-button:hover { background-color: #23272b; }
        .gmm-notification {
            position: fixed; bottom: 15px; left: 15px; padding: 12px; border-radius: 4px;
            color: white; z-index: 10000; font-size: 13px; box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            opacity: 0; transition: opacity 0.4s ease-in-out; max-width: 280px; word-wrap: break-word;
        }
        .gmm-notification.show { opacity: 1; }
        .gmm-notification.success { background-color: #28a745; }
        .gmm-notification.error { background-color: #dc3545; }
        .gmm-notification.info { background-color: #17a2b8; }
    `);

    function showNotification(message, type = 'info', duration = 4000) {
        let existingNotification = document.querySelector('.gmm-notification');
        if (existingNotification) existingNotification.remove();

        let notification = document.createElement('div');
        notification.className = `gmm-notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 10);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 450);
        }, duration);
    }

    function backendRequest(endpoint, params = {}, method = 'GET', customTimeout = DEFAULT_REQUEST_TIMEOUT) {
        return new Promise((resolve, reject) => {
            const urlParams = new URLSearchParams(params).toString();
            const fullUrl = `${BACKEND_URL}${endpoint}${urlParams ? '?' + urlParams : ''}`;
            GM_xmlhttpRequest({
                method: method,
                url: fullUrl,
                timeout: customTimeout,
                onload: function(response) {
                    try {
                        const data = JSON.parse(response.responseText);
                        if (response.status >= 200 && response.status < 300) resolve(data);
                        else reject(data.error || `HTTP Error ${response.status}`);
                    } catch (e) { reject(`Parse error. Response: ${response.responseText.substring(0,100)}`); }
                },
                onerror: function(response) { reject(`Request failed: ${response.statusText || 'Backend offline?'}`); },
                ontimeout: function() { reject(`Request timed out after ${customTimeout / 1000} seconds.`); }
            });
        });
    }

    function getModIdFromUrl() {
        return new URLSearchParams(window.location.search).get('id');
    }

    function isSupportedGameWorkshopItem() {
        if (!window.location.href.includes("steamcommunity.com/sharedfiles/filedetails/")) return false;
        const appNameElement = document.querySelector('.apphub_AppName');
        if (!appNameElement) return false;

        const appName = appNameElement.textContent.trim();
        return appName === 'People Playground' || appName === 'Project Zomboid';
    }

    async function updateModActionButtons(modId, buttonContainerDiv) {
        if (!modId || !buttonContainerDiv) return;
        buttonContainerDiv.innerHTML = '<button class="gmm-action-button loading">Loading Status...</button>';

        try {
            const status = await backendRequest('/is_installed', { id: modId });
            const updateInfo = status.installed ? await backendRequest('/check_update', { id: modId }) : null;

            buttonContainerDiv.innerHTML = '';

            let primaryButton = document.createElement('button');
            primaryButton.className = 'gmm-action-button';

            if (status.installed && updateInfo) {
                if (updateInfo.updateAvailable) {
                    primaryButton.textContent = `Update Mod (Steam: ${new Date(updateInfo.steamVersionTime * 1000).toLocaleDateString()})`;
                    primaryButton.classList.add('update');
                    primaryButton.onclick = () => handleGenericModAction('install', modId, 'Updating mod...', buttonContainerDiv, INSTALL_REQUEST_TIMEOUT);
                } else {
                    primaryButton.textContent = status.enabled ? 'Delete Mod' : `Delete Mod (Disabled)`;
                    primaryButton.classList.add('delete');
                    primaryButton.onclick = () => handleGenericModAction('delete', modId, 'Deleting mod...', buttonContainerDiv);
                }
            } else if (status.installed) {
                primaryButton.textContent = status.enabled ? 'Delete Mod' : `Delete Mod (Disabled)`;
                primaryButton.classList.add('delete');
                primaryButton.onclick = () => handleGenericModAction('delete', modId, 'Deleting mod...', buttonContainerDiv);
                showNotification('Could not check for mod update. Backend or Steam API issue?', 'error');
            }
             else {
                primaryButton.textContent = 'Install Mod';
                primaryButton.classList.add('install');
                primaryButton.onclick = () => handleGenericModAction('install', modId, 'Installing mod...', buttonContainerDiv, INSTALL_REQUEST_TIMEOUT);
            }
            buttonContainerDiv.appendChild(primaryButton);

            if (status.installed) {
                let toggleButton = document.createElement('button');
                toggleButton.className = `gmm-action-button ${status.enabled ? 'disable' : 'enable'}`;
                toggleButton.textContent = status.enabled ? 'Disable Mod' : 'Enable Mod';
                toggleButton.onclick = () => handleToggleModEnabled(modId, !status.enabled, buttonContainerDiv);
                buttonContainerDiv.appendChild(toggleButton);
            }

        } catch (error) {
            buttonContainerDiv.innerHTML = '';
            let errorButton = document.createElement('button');
            errorButton.className = 'gmm-action-button delete';
            errorButton.textContent = 'Backend Error';
            errorButton.disabled = true;
            buttonContainerDiv.appendChild(errorButton);
            showNotification(`Error fetching mod status: ${error}`, 'error');
        }
    }

    async function handleGenericModAction(action, modId, loadingMessage, buttonContainer, timeout = DEFAULT_REQUEST_TIMEOUT) {
        showNotification(loadingMessage, 'info', timeout - 1000);
        buttonContainer.querySelectorAll('.gmm-action-button').forEach(btn => {btn.disabled = true; btn.classList.add('loading');});
        try {
            const response = await backendRequest(`/${action}`, { id: modId }, 'GET', timeout);
            showNotification(response.message || `${action} ${response.success ? 'succeeded' : 'failed'}.`, response.success ? 'success' : 'error');
        } catch (error) {
            showNotification(`Error during ${action}: ${error}`, 'error');
        } finally {
            updateModActionButtons(modId, buttonContainer);
        }
    }

    async function handleToggleModEnabled(modId, enableState, buttonContainer) {
        const actionText = enableState ? "Enabling" : "Disabling";
        showNotification(`${actionText} mod...`, 'info', 10000);
        buttonContainer.querySelectorAll('.gmm-action-button').forEach(btn => {btn.disabled = true; btn.classList.add('loading');});
        try {
            const response = await backendRequest('/toggle_mod_enabled', { id: modId, enable: enableState.toString() });
            showNotification(response.message || `Toggle ${response.success ? 'succeeded' : 'failed'}.`, response.success ? 'success' : 'error');
        } catch (error) {
            showNotification(`Error ${actionText.toLowerCase()} mod: ${error}`, 'error');
        } finally {
            updateModActionButtons(modId, buttonContainer);
        }
    }

    function injectModPageButtons() {
        if (!isSupportedGameWorkshopItem()) return;
        const modId = getModIdFromUrl();
        if (!modId) return;

        let buttonContainerDiv = document.getElementById(`gmm-btn-container-${modId}`);
        if (buttonContainerDiv) {
            updateModActionButtons(modId, buttonContainerDiv);
            return;
        }

        buttonContainerDiv = document.createElement('div');
        buttonContainerDiv.id = `gmm-btn-container-${modId}`;
        buttonContainerDiv.className = 'gmm-button-container';

        const gameAreaPurchaseGame = document.querySelector('.game_area_purchase_game');
        let actionsArea = null;
        if (gameAreaPurchaseGame) {
            actionsArea = gameAreaPurchaseGame.querySelector('.actions');
        }

        if (actionsArea) {
            actionsArea.innerHTML = '';
            actionsArea.appendChild(buttonContainerDiv);
            updateModActionButtons(modId, buttonContainerDiv);
            return;
        }

        const subscribeButtonSelectors = [
            'a.subscribe.btn_green_white_innerfade',
            'div.subscribe.btn_green_white_innerfade',
            '.game_area_purchase_game .btn_subscribe',
            '#SubscribeItemBtn',
            '.workshopItemPublicActionSubscribe .btn_subscribe'
        ];
        let originalSubscribeButton = null;
        for (const selector of subscribeButtonSelectors) {
            originalSubscribeButton = document.querySelector(selector);
            if (originalSubscribeButton) break;
        }

        if (originalSubscribeButton && originalSubscribeButton.parentElement) {
            const parentOfSubscribeButton = originalSubscribeButton.parentElement;
            originalSubscribeButton.remove();
            parentOfSubscribeButton.appendChild(buttonContainerDiv);
            updateModActionButtons(modId, buttonContainerDiv);
            return;
        }

        const purchaseAreaBG = document.querySelector('.game_area_purchase_game_bg') || gameAreaPurchaseGame;
        if (purchaseAreaBG) {
            const steamButtonChild = purchaseAreaBG.querySelector('.btn_subscribe, .actions');
            if (steamButtonChild && steamButtonChild.parentElement === purchaseAreaBG) {
                steamButtonChild.remove();
            } else if (purchaseAreaBG !== gameAreaPurchaseGame && gameAreaPurchaseGame) {
                 const gameAreaSteamButton = gameAreaPurchaseGame.querySelector('.btn_subscribe, .actions');
                 if(gameAreaSteamButton) gameAreaSteamButton.remove();
            }
            let targetForAppend = purchaseAreaBG.querySelector('.block_content.block_content_inner') || purchaseAreaBG;
            targetForAppend.appendChild(buttonContainerDiv);
            updateModActionButtons(modId, buttonContainerDiv);
            return;
        }
        console.warn('[GMM] Could not find suitable DOM element to inject mod buttons reliably.');
    }

    function injectGlobalUpdateButton() {
         if (!window.location.href.includes("workshop") &&
             !(window.location.href.includes("app/1118200") || window.location.href.includes("app/108600"))) return;

         if (document.getElementById('gmm-global-update-btn')) return;

        const globalButton = document.createElement('button');
        globalButton.id = 'gmm-global-update-btn';
        globalButton.className = 'gmm-global-button';
        globalButton.textContent = 'Check All Mod Updates';
        document.body.appendChild(globalButton);

        globalButton.onclick = async () => {
            globalButton.textContent = 'Checking...'; globalButton.classList.add('loading'); globalButton.disabled = true;
            showNotification('Checking all installed mods for updates...', 'info', 10000);
            try {
                const response = await backendRequest('/check_updates', {}, 'GET', 60000);
                if (response.success && response.data) {
                    const updates = response.data.filter(mod => mod.updateAvailable);
                    if (updates.length > 0) {
                        let msg = `Updates available for:\n${updates.map(m => `${m.title || m.mod_id}`).join('\n')}`;
                        showNotification(msg, 'info', 15000); alert(msg);
                    } else if (response.data.length === 0) {
                        showNotification("No mods found or mods directory empty.", 'info');
                    } else {
                        showNotification("All mods are up-to-date!", 'success');
                    }
                } else { showNotification(response.message || "Failed to check for updates.", 'error'); }
            } catch (error) { showNotification(`Error checking all updates: ${error}`, 'error');
            } finally {
                globalButton.textContent = 'Check All Mod Updates'; globalButton.classList.remove('loading'); globalButton.disabled = false;
            }
        };
    }

    function initPyPPGScript() {
        injectModPageButtons();
        injectGlobalUpdateButton();
    }

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        initPyPPGScript();
    } else {
        document.addEventListener('DOMContentLoaded', initPyPPGScript);
    }

    let lastUrl = location.href;
    new MutationObserver(() => {
      const currentUrl = location.href;
      if (currentUrl !== lastUrl) {
        lastUrl = currentUrl;
        setTimeout(initPyPPGScript, 750);
      }
    }).observe(document.body, {subtree: true, childList: true});
})();
