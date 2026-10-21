// Contrôle complet de Mon club handisport (ordinateur, tablette, téléphones) avec les 246 clubs réels
const { chromium, devices } = require('/opt/node22/lib/node_modules/playwright');
const rows = require('./rows_db.json');
const URL = 'http://localhost:8765/index.html';
const results = [];
const ok = (zone, test, pass, info = '') => results.push({ zone, test, pass: !!pass, info: String(info).slice(0, 160) });

async function setup(ctx, opts = {}) {
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|409/.test(m.text())) errs.push(m.text()); });
  await p.route('**/*', r => {
    const u = r.request().url();
    if (u.includes('supabase.co/rest/v1/clubs')) {
      if (r.request().method() === 'POST') {
        const body = JSON.parse(r.request().postData());
        p._posts = (p._posts || []).concat([body]);
        return r.fulfill({ status: opts.postStatus || 201, body: '' });
      }
      return r.fulfill({ body: JSON.stringify(rows), contentType: 'application/json' });
    }
    if (/geocodage|api-adresse/.test(u)) return r.fulfill({ body: JSON.stringify({ features: [{ geometry: { coordinates: [-2.9 + Math.random() * .5, 48.3 + Math.random() * .4] } }] }), contentType: 'application/json' });
    if (u.includes('leaflet.min.js')) return r.fulfill({ path: 'node_modules/leaflet/dist/leaflet.js', contentType: 'text/javascript' });
    if (u.includes('leaflet.min.css')) return r.fulfill({ path: 'node_modules/leaflet/dist/leaflet.css', contentType: 'text/css' });
    if (u.includes('leaflet.markercluster.min.js')) return r.fulfill({ path: 'node_modules/leaflet.markercluster/dist/leaflet.markercluster.js', contentType: 'text/javascript' });
    if (u.includes('MarkerCluster.min.css')) return r.fulfill({ path: 'node_modules/leaflet.markercluster/dist/MarkerCluster.css', contentType: 'text/css' });
    if (u.includes('tile.openstreetmap') || u.includes('fonts.')) return r.fulfill({ body: '' });
    return r.continue();
  });
  p._errs = errs;
  return p;
}
const count = async p => parseInt((await p.textContent('#count')) || '0', 10);
const listNames = p => p.$$eval('#list .card h3', els => els.map(e => e.textContent));

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });

  // ================= MISE EN PAGE SUR 4 ÉCRANS =================
  for (const [nom, conf] of [
    ['Ordinateur 1366', { viewport: { width: 1366, height: 860 } }],
    ['Tablette 820 (appli)', { viewport: { width: 820, height: 1180 }, hasTouch: true, isMobile: true }],
    ['iPhone 13 (appli)', devices['iPhone 13']],
    ['Petit Android 360 (appli)', { viewport: { width: 360, height: 740 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3 }],
    ['iPhone 13 (site Safari)', devices['iPhone 13']],
    ['Petit Android 360 (site Chrome)', { viewport: { width: 360, height: 740 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3 }],
    ['Tablette 820 (site)', { viewport: { width: 820, height: 1180 }, hasTouch: true, isMobile: true }],
  ]) {
    const appli = nom.includes('(appli)');
    const ctx = await b.newContext({ ...conf, serviceWorkers: 'block' });
    const p = await setup(ctx);
    const t0 = Date.now();
    await p.goto(appli ? URL + '?mode=app' : URL); await p.waitForFunction(() => /club/.test(document.getElementById('count').textContent) && !/Chargement/.test(document.getElementById('count').textContent));
    ok(nom, 'Chargement des 246 clubs', await count(p) === 246, `${await count(p)} clubs en ${Date.now() - t0} ms`);
    const over = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    ok(nom, 'Pas de défilement horizontal', over <= 1, `débordement ${over}px`);
    const wide = await p.evaluate(() => [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1 && getComputedStyle(e).position !== 'fixed' && !e.closest('.chips,.leaflet-container,#sportChips,.hero-visual'); }).slice(0, 3).map(e => e.tagName + '.' + e.className));
    ok(nom, 'Aucun élément ne dépasse de l\'écran', wide.length === 0, wide.join(', '));
    if (appli) {
      const small = await p.evaluate(() => [...document.querySelectorAll('.tabbar button, #chips .chip:not(.sep), .card .fav, #openFilters, #near, .nav-actions .icon-btn')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.height < 40 || r.width < 40); }).map(e => (e.textContent.trim() || e.getAttribute('aria-label')) + ' ' + Math.round(e.getBoundingClientRect().height)));
      ok(nom, 'Zones tactiles assez grandes (≥ 40 px)', small.length === 0, small.slice(0, 4).join(' | '));
      ok(nom, 'Barre d\'onglets visible', await p.isVisible('.tabbar'));
      ok(nom, 'Partie « site » masquée (accueil ordinateur)', !(await p.isVisible('.hero')));
      const base = await p.evaluate(() => parseFloat(getComputedStyle(document.body).fontSize));
      ok(nom, 'Texte lisible (≥ 16 px)', base >= 16, base + 'px');
    } else {
      ok(nom, 'Accueil, chiffres et sports visibles', await p.isVisible('.hero') && await p.isVisible('#stats') && await p.isVisible('#sportsGrid'));
      ok(nom, 'Barre d\'onglets masquée', !(await p.isVisible('.tabbar')));
      ok(nom, 'Rubriques « Comment ça marche » et « À propos » visibles', await p.isVisible('#comment') && await p.isVisible('#apropos'));
      if (conf.isMobile) {
        ok(nom, 'Page défilable normalement (pas figée comme l\'appli)', await p.evaluate(() => document.documentElement.scrollHeight > innerHeight * 3));
        ok(nom, 'Bouton Liste / Carte visible', await p.isVisible('.view-toggle'));
        const small = await p.evaluate(() => [...document.querySelectorAll('.hero-search .btn, .view-toggle button, #chips .chip:not(.sep), .nav-actions .icon-btn, .sport-tile')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.height < 40; }).map(e => e.textContent.trim()));
        ok(nom, 'Zones tactiles assez grandes (≥ 40 px)', small.length === 0, small.slice(0, 4).join(' | '));
      }
    }
    await p.screenshot({ path: `qa-${nom.replace(/\W+/g, '_')}.png` });
    ok(nom, 'Aucune erreur JavaScript', p._errs.length === 0, p._errs.join(' | '));
    await ctx.close();
  }

  // ================= PARCOURS COMPLET SUR TÉLÉPHONE ET ORDINATEUR =================
  for (const [nom, conf] of [['iPhone 13', devices['iPhone 13']], ['Ordinateur', { viewport: { width: 1366, height: 860 } }]]) {
    const mobile = nom !== 'Ordinateur';
    const ctx = await b.newContext({ ...conf, serviceWorkers: 'block', geolocation: { latitude: 48.51, longitude: -2.76 }, permissions: ['geolocation'] });
    const p = await setup(ctx);
    const U = mobile ? URL + '?mode=app' : URL;
    await p.goto(U); await p.waitForFunction(() => /\d+ club/.test(document.getElementById('count').textContent));
    await p.waitForTimeout(1500);

    // --- Recherche
    await p.fill('#q', 'lannion'); await p.waitForTimeout(150);
    let n = await count(p); let names = await listNames(p);
    ok(nom, 'Recherche « lannion »', n > 0 && n < 246, `${n} résultats`);
    await p.fill('#q', 'equitation'); await p.waitForTimeout(150);
    ok(nom, 'Recherche sans accent (« equitation » trouve « équitation »)', await count(p) > 0, `${await count(p)} résultats`);
    await p.fill('#q', 'zzzz'); await p.waitForTimeout(150);
    ok(nom, 'Aucun résultat : message + bouton « Tout effacer »', await p.isVisible('.state') && await p.isVisible('.state button'));
    await p.click('#clearQ'); await p.waitForTimeout(150);
    ok(nom, 'Bouton effacer la recherche', await count(p) === 246 && (await p.inputValue('#q')) === '');

    // --- Puce sport
    const chip = p.locator('#sportChips [data-sport]').first();
    const chipTxt = await chip.textContent(); const chipN = parseInt(chipTxt.match(/(\d+)$/)[1], 10);
    await chip.scrollIntoViewIfNeeded(); await chip.click(); await p.waitForTimeout(150);
    ok(nom, `Filtre sport (« ${chipTxt.replace(/\d+$/, '')} »)`, await count(p) === chipN, `${await count(p)} / attendu ${chipN}`);
    await p.locator('#sportChips [data-sport][aria-pressed="true"]').click(); await p.waitForTimeout(150);
    ok(nom, 'Désactiver le filtre sport', await count(p) === 246);

    // --- Feuille de filtres
    await p.click('#openFilters'); await p.waitForTimeout(350);
    ok(nom, 'Ouvrir les filtres', await p.evaluate(() => document.getElementById('filters').open));
    const bodyH = await p.evaluate(() => document.querySelector('#filters .sheet-body').getBoundingClientRect().height);
    ok(nom, 'Contenu des filtres visible (hauteur > 200 px)', bodyH > 200, Math.round(bodyH) + 'px');
    await p.locator('#fHandicaps label:has-text("Visuel")').click(); await p.waitForTimeout(100);
    const nVis = await count(p);
    const vis = await p.evaluate(() => filtered().every(c => c.handicaps.includes('visuel')));
    ok(nom, 'Filtre handicap visuel', vis && nVis > 0, `${nVis} clubs`);
    await p.locator('#fPratique label:has-text("Sport adapté")').click(); await p.waitForTimeout(100);
    ok(nom, 'Filtre pratique « sport adapté »', await p.evaluate(() => filtered().every(c => ['sport adapte', 'les deux'].includes(c.pratique))));
    await p.selectOption('#fReg', 'Bretagne'); await p.waitForTimeout(100);
    const deps = await p.locator('#fDep option').allTextContents();
    ok(nom, 'Région Bretagne → départements bretons seulement', deps.length > 1 && deps.slice(1).every(d => /\((22|29|35|56)\)/.test(d)), deps.slice(1).join(', '));
    await p.selectOption('#fDep', '22'); await p.waitForTimeout(100);
    ok(nom, 'Filtre département 22', await p.evaluate(() => filtered().every(c => c.dep === '22')));
    const btn = await p.textContent('#fApply'); const shown = await count(p);
    ok(nom, 'Bouton « Voir N clubs » = nombre affiché', btn.includes(String(shown)) || (shown === 0 && /Aucun/.test(btn)), `${btn} / ${shown}`);
    ok(nom, 'Badge du nombre de filtres actifs', (await p.textContent('#filterBadge')) === '4', await p.textContent('#filterBadge'));
    await p.click('#fTrust'); await p.waitForTimeout(100);
    ok(nom, 'Interrupteur « Clubs expérimentés »', await p.evaluate(() => filtered().every(c => c.paraClub)));
    await p.click('#fReset'); await p.waitForTimeout(100);
    ok(nom, 'Effacer les filtres', await count(p) === 246 && !(await p.isVisible('#filterBadge')));
    await p.click('#fApply'); await p.waitForTimeout(350);
    ok(nom, 'Fermer les filtres', !(await p.evaluate(() => document.getElementById('filters').open)));

    // --- Tri
    await p.selectOption('#sort', 'az'); await p.waitForTimeout(150);
    names = await listNames(p);
    ok(nom, 'Tri de A à Z', names.slice(0, 15).every((x, i, a) => i === 0 || a[i - 1].localeCompare(x, 'fr') <= 0), names.slice(0, 3).join(' / '));
    await p.click('#near'); await p.waitForTimeout(800);
    const dists = await p.evaluate(() => filtered().slice(0, 20).map(c => c.dist));
    ok(nom, '« Autour de moi » : tri par distance', dists.every((d, i) => d != null && (i === 0 || dists[i - 1] <= d)), dists.slice(0, 3).map(d => d && d.toFixed(1)).join(' / ') + ' km');
    ok(nom, 'Distance affichée sur les fiches', await p.locator('#list .card .dist').count() > 0);
    const zNear = await p.evaluate(() => map.getZoom());
    ok(nom, '« Autour de moi » : carte centrée près de toi', zNear >= 9, 'zoom ' + zNear);
    await p.click('#near'); await p.waitForTimeout(150);
    ok(nom, 'Désactiver « Autour de moi »', (await p.inputValue('#sort')) === 'reco');

    // --- Pagination
    ok(nom, '30 fiches puis « Voir plus »', await p.locator('#list .card').count() === 30 && await p.isVisible('.more button'));
    await p.click('.more button'); await p.waitForTimeout(150);
    ok(nom, '« Voir plus » ajoute 30 fiches', await p.locator('#list .card').count() === 60);

    // --- Fiche club
    const multi = rows.find(r => r.sport.includes(',') && r.telephone && r.email);
    await p.evaluate(id => openDetail(String(id)), multi.id); await p.waitForTimeout(400);
    ok(nom, 'Ouvrir une fiche', await p.evaluate(() => document.getElementById('detail').open), multi.nom);
    const dH = await p.evaluate(() => document.getElementById('dBody').getBoundingClientRect().height);
    ok(nom, 'Détails visibles dans la fiche', dH > 150, Math.round(dH) + 'px');
    const hrefs = await p.$$eval('#dBody .actions a', as => as.map(a => a.getAttribute('href')));
    ok(nom, 'Bouton Appeler (tel:)', hrefs.some(h => /^tel:\+?\d{9,}/.test(h)), hrefs.find(h => h.startsWith('tel')));
    ok(nom, 'Bouton Écrire (mailto:)', hrefs.some(h => h.startsWith('mailto:')));
    ok(nom, 'Bouton Itinéraire (Google Maps)', hrefs.some(h => h.includes('google.com/maps/dir')));
    ok(nom, 'Liste des sports du club', await p.isVisible('#dBody .sec h3:has-text("Sports proposés")'));
    ok(nom, 'Lien « Signaler une correction »', (await p.getAttribute('#dBody .report a', 'href')).startsWith('mailto:'));
    ok(nom, 'Adresse du lien partagé (#club-…)', await p.evaluate(() => location.hash) === '#club-' + multi.id);
    const noSite = rows.find(r => !r.site);
    await p.goBack(); await p.waitForTimeout(300);
    ok(nom, 'Retour arrière ferme la fiche', !(await p.evaluate(() => document.getElementById('detail').open)) && await p.evaluate(() => location.hash) === '');
    await p.evaluate(id => openDetail(String(id)), noSite.id); await p.waitForTimeout(300);
    ok(nom, 'Bouton Site grisé si pas de site', await p.locator('#dBody .act[aria-disabled="true"]:has-text("Site")').count() === 1);
    await p.keyboard.press('Escape'); await p.waitForTimeout(300);
    ok(nom, 'Touche Échap ferme la fiche', !(await p.evaluate(() => document.getElementById('detail').open)));
    await p.evaluate(id => openDetail(String(id)), noSite.id); await p.waitForTimeout(300);
    await p.click('#detail [data-close]'); await p.waitForTimeout(300);
    ok(nom, 'Croix ferme la fiche', !(await p.evaluate(() => document.getElementById('detail').open)));

    // --- Partage (sans navigator.share → copie du lien)
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write']);
    await p.evaluate(() => { delete Navigator.prototype.share; });
    await p.evaluate(id => openDetail(String(id)), multi.id); await p.waitForTimeout(300);
    await p.click('#dShare'); await p.waitForTimeout(300);
    ok(nom, 'Partager → « Lien copié »', (await p.textContent('#toast')).includes('Lien copié'));
    await p.click('#detail [data-close]'); await p.waitForTimeout(300);

    // --- Favoris (et conservation après rechargement)
    await p.locator('#list .card .fav').first().click(); await p.locator('#list .card .fav').nth(1).click(); await p.waitForTimeout(200);
    ok(nom, 'Ajout de 2 favoris', (await p.textContent('#favBadge')) === '2');
    await p.reload(); await p.waitForFunction(() => /\d+ club/.test(document.getElementById('count').textContent));
    ok(nom, 'Favoris conservés après rechargement', (await p.textContent('#favBadge')) === '2');
    if (mobile) await p.click('.tabbar [data-tab="favoris"]'); else await p.click('#favChip');
    await p.waitForTimeout(200);
    ok(nom, 'Affichage des favoris seulement', await count(p) === 2);
    if (mobile) await p.click('.tabbar [data-tab="liste"]'); else await p.click('#favChip');
    await p.waitForTimeout(200);

    // --- Lien direct vers une fiche
    await p.goto(U + '#club-' + multi.id); await p.waitForTimeout(1500);
    ok(nom, 'Lien direct vers une fiche', await p.evaluate(() => document.getElementById('detail').open) && (await p.textContent('#dName')) === multi.nom);
    await p.goto(U + '#club-999999'); await p.waitForTimeout(1200);
    ok(nom, 'Lien vers une fiche inexistante ignoré', !(await p.evaluate(() => document.getElementById('detail').open)));
    await p.goto(U); await p.waitForTimeout(1500);

    // --- Carte
    if (mobile) { await p.click('.tabbar [data-tab="carte"]'); await p.waitForTimeout(800); }
    ok(nom, 'Carte affichée', await p.isVisible('#map'));
    const nm = await p.evaluate(() => cluster.getLayers().length);
    ok(nom, 'Un repère par club', nm === 246, nm + ' repères');
    await p.evaluate(() => { const m = [...markers.values()][0]; m.fire('click'); }); await p.waitForTimeout(300);
    ok(nom, 'Toucher un repère → aperçu du club', await p.isVisible('#peek'));
    await p.click('#peek .btn'); await p.waitForTimeout(400);
    ok(nom, 'Aperçu → fiche complète', await p.evaluate(() => document.getElementById('detail').open));
    await p.click('#detail [data-close]'); await p.waitForTimeout(300);
    await p.click('#mapLocate'); await p.waitForTimeout(800);
    ok(nom, 'Bouton « Me localiser » sur la carte', await p.evaluate(() => map.getZoom()) === 13);

    if (mobile) {
      await p.click('.tabbar [data-tab="infos"]'); await p.waitForTimeout(300);
      ok(nom, 'Onglet Infos (comment ça marche, à propos)', await p.isVisible('#comment') && await p.isVisible('#apropos'));
      await p.click('.tabbar [data-tab="liste"]'); await p.waitForTimeout(300);
      await p.evaluate(() => document.getElementById('paneList').scrollTop = 500); await p.waitForTimeout(400);
      ok(nom, 'En-tête qui se replie au défilement', await p.evaluate(() => document.getElementById('siteNav').classList.contains('compact')));
    } else {
      // --- Partie site (ordinateur)
      await p.goto(URL); await p.waitForTimeout(1500);
      ok(nom, 'Chiffres clés calculés', (await p.locator('.stat b').allTextContents()).every(x => /^\d+$/.test(x)), (await p.locator('.stat b').allTextContents()).join(' / '));
      await p.fill('#heroQ', 'Besançon'); await p.press('#heroQ', 'Enter'); await p.waitForTimeout(900);
      ok(nom, 'Recherche de l\'accueil → annuaire filtré', (await p.inputValue('#q')) === 'Besançon' && await count(p) > 0 && await p.evaluate(() => scrollY) > 500, `${await count(p)} clubs`);
      await p.evaluate(() => resetAll()); await p.evaluate(() => scrollTo(0, 0));
      await p.locator('#popular button').first().click(); await p.waitForTimeout(800);
      ok(nom, 'Sports populaires de l\'accueil', await p.evaluate(() => !!state.sport));
      await p.evaluate(() => resetAll());
      const tiles = await p.locator('.sport-tile').count();
      await p.click('#allSports'); await p.waitForTimeout(150);
      ok(nom, 'Vignettes de sports + « Tous les sports »', tiles === 16 && await p.locator('.sport-tile').count() > 16, `${tiles} → ${await p.locator('.sport-tile').count()}`);
      for (const [a, id] of [['Comment ça marche', 'comment'], ['À propos', 'apropos'], ['Trouver un club', 'annuaire']]) {
        await p.click(`.nav-links a:has-text("${a}")`); await p.waitForTimeout(700);
        const top = await p.evaluate(i => document.getElementById(i).getBoundingClientRect().top, id);
        ok(nom, `Menu « ${a} »`, Math.abs(top) < 120, `position ${Math.round(top)}`);
      }
      // Clavier
      await p.evaluate(() => scrollTo(0, 0));
      await p.focus('#list .card'); await p.keyboard.press('Enter'); await p.waitForTimeout(300);
      ok(nom, 'Clavier : Entrée ouvre une fiche', await p.evaluate(() => document.getElementById('detail').open));
      await p.keyboard.press('Escape'); await p.waitForTimeout(200);
    }

    // --- Formulaire « Inscrire un club »
    await p.goto(U); await p.waitForTimeout(1500);
    await p.locator('.suggest:visible').first().click(); await p.waitForTimeout(400);
    ok(nom, 'Ouvrir le formulaire', await p.evaluate(() => document.getElementById('propose').open));
    await p.click('#pSend'); await p.waitForTimeout(100);
    ok(nom, 'Formulaire vide refusé', (await p.textContent('#pError')).length > 0, await p.textContent('#pError'));
    await p.fill('#pNom', 'QA Club Test'); await p.fill('#pSport', 'judo, natation'); await p.fill('#pCp', '1234'); await p.fill('#pVille', 'Rennes'); await p.locator('#pOk').check();
    await p.click('#pSend'); await p.waitForTimeout(100);
    ok(nom, 'Code postal invalide refusé', /code postal/i.test(await p.textContent('#pError')));
    await p.fill('#pCp', '35000'); await p.fill('#pEmail', 'pas-un-email'); await p.click('#pSend'); await p.waitForTimeout(100);
    ok(nom, 'Email invalide refusé', /email/i.test(await p.textContent('#pError')));
    await p.fill('#pEmail', 'club@exemple.fr'); await p.click('#pSend'); await p.waitForTimeout(800);
    const post = (p._posts || [])[0];
    ok(nom, 'Envoi : 1 fiche avec tous les sports, masquée', post && post.length === 1 && post[0].sport === 'judo, natation' && post[0].publie === false, post && JSON.stringify(post[0]).slice(0, 90));
    ok(nom, 'Message de confirmation', await p.isVisible('.done'));
    await p.click('.done [data-close]'); await p.waitForTimeout(300);
    await p.locator('.suggest:visible').first().click(); await p.waitForTimeout(300);
    ok(nom, 'Formulaire vierge à la réouverture', await p.isVisible('#pNom') && (await p.inputValue('#pNom')) === '');
    await p.evaluate(() => closeSheet(document.getElementById('propose'))); await p.waitForTimeout(300);
    ok(nom, 'Aucune erreur JavaScript pendant le parcours', p._errs.length === 0, p._errs.join(' | '));
    await ctx.close();
  }

  // ================= SITE DANS SAFARI SUR IPHONE =================
  {
    const nom = 'Site sur iPhone';
    const ctx = await b.newContext({ ...devices['iPhone 13'], serviceWorkers: 'block', geolocation: { latitude: 47.24, longitude: 6.02 }, permissions: ['geolocation'] });
    const p = await setup(ctx);
    await p.goto(URL); await p.waitForTimeout(1800);
    ok(nom, 'Mode site (pas le mode appli)', !(await p.evaluate(() => document.documentElement.classList.contains('app'))));
    await p.fill('#heroQ', 'Besançon'); await p.press('#heroQ', 'Enter'); await p.waitForTimeout(900);
    ok(nom, 'Recherche de l\'accueil → annuaire filtré', (await p.inputValue('#q')) === 'Besançon' && await count(p) > 0 && await p.evaluate(() => document.getElementById('annuaire').getBoundingClientRect().top) < 120, `${await count(p)} clubs`);
    await p.evaluate(() => resetAll());
    await p.locator('.sport-tile').first().click(); await p.waitForTimeout(800);
    ok(nom, 'Vignette sport → annuaire filtré', await p.evaluate(() => !!state.sport) && await p.evaluate(() => document.getElementById('annuaire').getBoundingClientRect().top) < 120);
    await p.evaluate(() => resetAll());
    await p.locator('.view-toggle [data-view="carte"]').click(); await p.waitForTimeout(800);
    const mh = await p.evaluate(() => document.getElementById('map').getBoundingClientRect().height);
    ok(nom, 'Bouton « Carte » : carte affichée avec les repères', mh > 300 && await p.evaluate(() => cluster.getLayers().length) === 246, Math.round(mh) + ' px');
    await p.evaluate(() => { const m = [...markers.values()][0]; m.fire('click'); }); await p.waitForTimeout(300);
    ok(nom, 'Repère → aperçu du club', await p.isVisible('#peek'));
    await p.locator('.view-toggle [data-view="liste"]').click(); await p.waitForTimeout(300);
    ok(nom, 'Bouton « Liste » : retour à la liste', await p.isVisible('#list .card') && !(await p.isVisible('#map')));
    await p.locator('#list .card').first().click(); await p.waitForTimeout(400);
    ok(nom, 'Fiche club avec détails', await p.evaluate(() => document.getElementById('detail').open) && await p.evaluate(() => document.getElementById('dBody').getBoundingClientRect().height) > 150);
    await p.click('#detail [data-close]'); await p.waitForTimeout(300);
    await p.click('#near'); await p.waitForTimeout(900);
    ok(nom, '« Autour de moi » : tri par distance', await p.evaluate(() => state.sort === 'near' && filtered()[0].dist != null), await p.evaluate(() => (filtered()[0].dist || 0).toFixed(1) + ' km'));
    await p.click('.nav-actions .icon-btn.suggest'); await p.waitForTimeout(400);
    ok(nom, 'Bouton « + » : formulaire d\'inscription', await p.evaluate(() => document.getElementById('propose').open));
    await p.evaluate(() => closeSheet(document.getElementById('propose'))); await p.waitForTimeout(300);
    await p.locator('#apropos .suggest').click(); await p.waitForTimeout(400);
    ok(nom, '« Inscrire mon club » (À propos) : formulaire', await p.evaluate(() => document.getElementById('propose').open));
    await p.screenshot({ path: 'qa-site-iphone.png', fullPage: false });
    ok(nom, 'Aucune erreur JavaScript', p._errs.length === 0, p._errs.join(' | '));
    await ctx.close();
  }

  // ================= CAS PARTICULIERS =================
  {
    const ctx = await b.newContext({ ...devices['iPhone 13'], serviceWorkers: 'block' });
    const p = await setup(ctx, { postStatus: 409 });
    await p.goto(URL + '?mode=app'); await p.waitForTimeout(1500);
    await p.locator('.suggest:visible').first().click(); await p.waitForTimeout(400);
    await p.fill('#pNom', 'Handisport 2.0'); await p.fill('#pSport', 'boccia'); await p.fill('#pCp', '93000'); await p.fill('#pVille', 'Bobigny'); await p.locator('#pOk').check();
    await p.click('#pSend'); await p.waitForTimeout(800);
    ok('Cas particuliers', 'Club déjà présent : message clair', /déjà dans l'annuaire/.test(await p.textContent('#pError')));
    await ctx.close();
  }
  {
    const ctx = await b.newContext({ ...devices['iPhone 13'], serviceWorkers: 'block' });
    const p = await setup(ctx);
    await p.route(/supabase\.co/, r => r.fulfill({ status: 500, body: 'down' }));
    await p.goto(URL); await p.waitForTimeout(1500);
    ok('Cas particuliers', 'Base indisponible : message + bouton Recharger', /Impossible/.test(await p.textContent('#count')) && await p.isVisible('.state .btn'));
    await ctx.close();
  }
  {
    const ctx = await b.newContext({ ...devices['iPhone 13'], serviceWorkers: 'block', geolocation: { latitude: 0, longitude: 0 }, permissions: [] });
    const p = await setup(ctx);
    await p.goto(URL); await p.waitForTimeout(1500);
    await p.click('#near'); await p.waitForTimeout(1500);
    ok('Cas particuliers', 'Localisation refusée : message', /refusée/.test(await p.textContent('#geoStatus')), await p.textContent('#geoStatus'));
    await ctx.close();
  }
  for (const [nom, conf] of [['Mode sombre iPhone', devices['iPhone 13']], ['Mode sombre ordinateur', { viewport: { width: 1366, height: 860 } }]]) {
    const ctx = await b.newContext({ ...conf, colorScheme: 'dark', serviceWorkers: 'block' });
    const p = await setup(ctx);
    await p.goto(URL); await p.waitForTimeout(1500);
    const bg = await p.evaluate(() => getComputedStyle(document.body).backgroundColor);
    ok(nom, 'Fond sombre appliqué', bg === 'rgb(18, 26, 34)', bg);
    await p.evaluate(() => openDetail(String(filtered()[0].id))); await p.waitForTimeout(400);
    const c = await p.evaluate(() => { const e = document.querySelector('#dBody .act'); const s = getComputedStyle(e); return [s.color, s.backgroundColor]; });
    ok(nom, 'Boutons lisibles en mode sombre', c[0] !== c[1], c.join(' sur '));
    await p.screenshot({ path: `qa-${nom.replace(/\W+/g, '_')}.png` });
    await ctx.close();
  }

  // ================= RÉFÉRENCEMENT ET APPLI INSTALLABLE =================
  {
    const ctx = await b.newContext({ viewport: { width: 1366, height: 860 }, serviceWorkers: 'block' });
    const p = await setup(ctx);
    await p.goto(URL); await p.waitForTimeout(1000);
    const meta = await p.evaluate(() => ({
      title: document.title, desc: document.querySelector('meta[name=description]')?.content,
      canon: document.querySelector('link[rel=canonical]')?.href, og: document.querySelector('meta[property="og:image"]')?.content,
      lang: document.documentElement.lang, h1: document.querySelectorAll('h1').length, ld: !!document.querySelector('script[type="application/ld+json"]'),
      noname: [...document.querySelectorAll('button, a[href]')].filter(e => e.offsetParent && !(e.textContent.trim() || e.getAttribute('aria-label') || e.getAttribute('title'))).length,
    }));
    ok('Référencement', 'Titre et description', meta.title.length > 20 && meta.desc && meta.desc.length > 80, meta.title);
    ok('Référencement', 'Adresse canonique, image de partage, données structurées', meta.canon && meta.og && meta.ld);
    ok('Accessibilité', 'Langue française déclarée', meta.lang === 'fr');
    ok('Accessibilité', 'Tous les boutons et liens ont un nom', meta.noname === 0, meta.noname + ' sans nom');
    for (const f of ['manifest.webmanifest', 'sw.js', 'robots.txt', 'sitemap.xml', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png', 'icon-maskable-512.png']) {
      const r = await p.request.get('http://localhost:8765/' + f);
      ok('Appli installable', `Fichier ${f}`, r.ok(), r.status());
    }
    const man = await (await p.request.get('http://localhost:8765/manifest.webmanifest')).json();
    ok('Appli installable', 'Manifeste complet (nom, icônes, plein écran)', man.name && man.icons.length >= 2 && man.display === 'standalone', man.name);
    await ctx.close();
  }

  await b.close();
  const zones = [...new Set(results.map(r => r.zone))];
  for (const z of zones) {
    console.log(`\n### ${z}`);
    for (const r of results.filter(x => x.zone === z)) console.log(`${r.pass ? 'OK  ' : 'ÉCHEC'} ${r.test}${r.info ? '  — ' + r.info : ''}`);
  }
  const fails = results.filter(r => !r.pass);
  console.log(`\nTOTAL : ${results.length - fails.length}/${results.length} réussis`);
})().catch(e => { console.error('ARRÊT DU TEST :', e.message.split('\n')[0]); console.log(results.map(r => `${r.pass ? 'OK' : 'ÉCHEC'} [${r.zone}] ${r.test} ${r.info}`).join('\n')); });
