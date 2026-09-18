/* ===================================================================
   나를 성장시키는 메모 — 인터랙션 레이어

   원칙: 점진적 향상(progressive enhancement).
   이 파일이 통째로 실패해도 모든 폼은 일반 제출로 그대로 동작합니다.
   서버 라우트(/add, /edit/{id}, /delete/{id})는 건드리지 않고
   똑같은 엔드포인트를 fetch로 부를 뿐입니다.

   구성
     0. 유틸
     1. 토스트
     2. 서버 동기화 (낙관적 UI + 실패 시 롤백)
     3. 완료 토글
     4. 인라인 이름 바꾸기
     5. 삭제 + 실행 취소
     6. 추가 (새로고침 없이)
     7. 필터 + FLIP 애니메이션
     8. 진행률 링
     9. 테마 전환 (원형 와이프)
    10. 명령 팔레트
    11. 키보드 단축키
   =================================================================== */

(() => {
  'use strict';

  const root = document.documentElement;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* === 0. 유틸 ===================================================== */
  const $  = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  const list = $('[data-list]');

  /** 폼 데이터를 그대로 POST — 서버가 기대하는 형식 그대로 보냅니다 */
  const post = (url, data) =>
    fetch(url, {
      method: 'POST',
      body: new URLSearchParams(data),
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

  /* === 1. 토스트 =================================================== */
  const toastRegion = $('[data-toasts]');

  function toast(message, { action, onAction, timeout = 5000 } = {}) {
    if (!toastRegion) return;

    const el = document.createElement('div');
    el.className = 'toast';
    el.innerHTML = `<span class="toast-msg"></span>`;
    $('.toast-msg', el).textContent = message;

    if (action) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'toast-action';
      btn.textContent = action;
      btn.addEventListener('click', () => { close(); onAction?.(); });
      el.append(btn);
    }

    let done = false;
    const close = () => {
      if (done) return;
      done = true;
      el.classList.add('is-out');
      el.addEventListener('transitionend', () => el.remove(), { once: true });
      setTimeout(() => el.remove(), 400);  // transition이 안 걸릴 때 대비
    };

    toastRegion.append(el);
    requestAnimationFrame(() => el.classList.add('is-in'));
    setTimeout(close, timeout);
    return close;
  }

  /* === 2. 서버 동기화 ==============================================
     낙관적으로 화면을 먼저 바꾸고, 서버 응답이 오면 조용히 맞춥니다.
     실패하면 되돌리고 알려줍니다. */
  async function syncFromServer() {
    if (!list) return;
    const html = await fetch('/', { headers: { 'X-Requested-With': 'fetch' } }).then(r => r.text());
    const fresh = new DOMParser().parseFromString(html, 'text/html').querySelector('[data-list]');
    if (!fresh) return;

    // 현재 화면에 없는 항목만 추가하고, 사라진 항목은 제거 — 통째로 갈아끼우면
    // 진행 중인 애니메이션이 끊기기 때문입니다.
    const freshIds = new Set($$('.task', fresh).map(t => t.dataset.id));
    $$('.task', list).forEach(t => { if (!freshIds.has(t.dataset.id)) t.remove(); });

    const haveIds = new Set($$('.task', list).map(t => t.dataset.id));
    $$('.task', fresh).forEach((t, i) => {
      if (!haveIds.has(t.dataset.id)) {
        t.style.setProperty('--i', i);
        const at = list.children[i];
        at ? list.insertBefore(t, at) : list.append(t);
      }
    });

    applyFilter(currentFilter, { animate: false });
    updateProgress();
  }

  /** 실패 시 사용자에게 알리고 화면을 서버 상태로 되돌립니다 */
  async function fail(msg) {
    toast(msg);
    await syncFromServer().catch(() => location.reload());
  }

  /* === 3. 완료 토글 ================================================ */
  function paintDone(task, done) {
    task.classList.toggle('is-done', done);
    task.dataset.done = done ? '1' : '0';
    const btn = $('.toggle', task);
    if (btn) btn.setAttribute('aria-pressed', String(done));

    // 완료로 바뀌는 순간에만 취소선을 그려 넣습니다
    if (done && !reduceMotion) {
      const text = $('[data-text]', task);
      text?.classList.remove('strike-in');
      void text?.offsetWidth;          // 리플로우 강제 — 애니메이션 재시작용
      text?.classList.add('strike-in');
    }
  }

  async function toggleDone(task) {
    const done = task.dataset.done !== '1';
    paintDone(task, done);             // 먼저 화면부터 바꿉니다
    updateProgress();
    if (currentFilter !== 'all') applyFilter(currentFilter);

    try {
      const body = { task: task.dataset.task };
      if (done) body.completed = 'true';
      const res = await post(`/edit/${task.dataset.id}`, body);
      if (!res.ok) throw new Error(res.status);
    } catch {
      paintDone(task, !done);          // 롤백
      updateProgress();
      fail('저장하지 못했어요. 잠시 후 다시 시도해주세요.');
    }
  }

  /* === 4. 인라인 이름 바꾸기 =======================================
     항목 텍스트를 눌러 그 자리에서 고칩니다. Enter 저장 / Esc 취소. */
  function startRename(task) {
    const text = $('[data-text]', task);
    if (!text || text.isContentEditable) return;

    const before = task.dataset.task;
    text.contentEditable = 'plaintext-only';
    if (text.contentEditable !== 'plaintext-only') text.contentEditable = 'true';
    task.classList.add('is-editing');
    text.focus();

    // 캐럿을 끝으로
    const range = document.createRange();
    range.selectNodeContents(text);
    range.collapse(false);
    const sel = getSelection();
    sel.removeAllRanges();
    sel.addRange(range);

    const finish = async (save) => {
      text.contentEditable = 'false';
      task.classList.remove('is-editing');
      text.removeEventListener('keydown', onKey);
      text.removeEventListener('blur', onBlur);

      const next = text.textContent.trim();
      if (!save || !next || next === before) {
        text.textContent = before;     // 되돌리기
        return;
      }

      task.dataset.task = next;
      $('.toggle-form [name="task"]', task)?.setAttribute('value', next);

      try {
        const body = { task: next };
        if (task.dataset.done === '1') body.completed = 'true';
        const res = await post(`/edit/${task.dataset.id}`, body);
        if (!res.ok) throw new Error(res.status);
        toast('바꿨어요');
      } catch {
        task.dataset.task = before;
        text.textContent = before;
        fail('이름을 바꾸지 못했어요.');
      }
    };

    const onKey = (e) => {
      if (e.key === 'Enter') { e.preventDefault(); finish(true); }
      if (e.key === 'Escape') { e.preventDefault(); finish(false); }
    };
    const onBlur = () => finish(true);

    text.addEventListener('keydown', onKey);
    text.addEventListener('blur', onBlur);
  }

  /* === 5. 삭제 + 실행 취소 ========================================= */
  async function removeTask(task) {
    const id    = task.dataset.id;
    const label = task.dataset.task;
    const done  = task.dataset.done === '1';

    // 높이를 접으면서 사라지게 합니다
    const h = task.offsetHeight;
    task.style.height = `${h}px`;
    task.classList.add('is-removing');
    requestAnimationFrame(() => { task.style.height = '0px'; });
    setTimeout(() => task.remove(), reduceMotion ? 0 : 260);

    updateProgress();

    try {
      const res = await post(`/delete/${id}`, {});
      if (!res.ok) throw new Error(res.status);
    } catch {
      return fail('삭제하지 못했어요.');
    }

    toast('삭제했어요', {
      action: '실행 취소',
      onAction: async () => {
        try {
          // 원래 id는 이미 없어졌으므로 같은 내용으로 새로 만듭니다
          await post('/add', { task: label });
          await syncFromServer();
          if (done) {
            const again = $$('.task', list).find(t => t.dataset.task === label);
            if (again) await toggleDone(again);
          }
          toast('되돌렸어요');
        } catch {
          fail('되돌리지 못했어요.');
        }
      },
    });
  }

  /* === 6. 추가 (새로고침 없이) ===================================== */
  const addForm = $('[data-add-form]');

  addForm?.addEventListener('submit', async (e) => {
    const field = $('#task', addForm);
    const value = field.value.trim();

    if (!value) { e.preventDefault(); field.focus(); return; }

    e.preventDefault();
    const btn = $('button[type="submit"]', addForm);
    btn.disabled = true;                     // 두 번 눌러 중복 저장되는 걸 막습니다
    field.value = '';
    field.style.height = '';

    try {
      const res = await post('/add', { task: value });
      if (!res.ok) throw new Error(res.status);
      await syncFromServer();
      toast('추가했어요');
    } catch {
      field.value = value;                   // 입력 내용은 잃지 않게 되돌립니다
      fail('추가하지 못했어요.');
    } finally {
      btn.disabled = false;
      field.focus();
    }
  });

  /* === 7. 필터 + FLIP 애니메이션 ===================================
     FLIP = 바꾸기 전 위치를 재고(First/Last), 차이만큼 되돌린 뒤(Invert)
     0으로 애니메이션(Play). 위치 이동이 매끄러워집니다. */
  let currentFilter = 'all';

  function applyFilter(kind, { animate = true } = {}) {
    if (!list) return;
    currentFilter = kind;

    const tasks = $$('.task', list);
    const first = new Map(tasks.map(t => [t, t.getBoundingClientRect().top]));

    tasks.forEach(t => {
      const done = t.dataset.done === '1';
      const show = kind === 'all' || (kind === 'done' ? done : !done);
      t.classList.toggle('is-hidden', !show);
    });

    if (animate && !reduceMotion) {
      tasks.forEach(t => {
        if (t.classList.contains('is-hidden')) return;
        const delta = first.get(t) - t.getBoundingClientRect().top;
        if (!delta) return;
        t.animate(
          [{ transform: `translateY(${delta}px)` }, { transform: 'none' }],
          { duration: 260, easing: 'cubic-bezier(0.16, 1, 0.3, 1)' }
        );
      });
    }

    $$('[data-filter]').forEach(b => {
      const on = b.dataset.filter === kind;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-pressed', String(on));
    });

    list.classList.toggle('is-filtered-empty', !tasks.some(t => !t.classList.contains('is-hidden')));
  }

  $('[data-filters]')?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-filter]');
    if (btn) applyFilter(btn.dataset.filter);
  });

  /* === 8. 진행률 링 ================================================ */
  const ring      = $('[data-ring]');
  const ringFill  = $('[data-ring-fill]');
  const ringLabel = $('[data-ring-label]');
  const ringSr    = $('[data-ring-sr]');
  const CIRC = 2 * Math.PI * 15;   // r=15

  function updateProgress() {
    if (!ring || !list) return;
    const tasks = $$('.task', list);
    const total = tasks.length;
    const done  = tasks.filter(t => t.dataset.done === '1').length;

    ring.hidden = total === 0;
    if (!total) return;

    const pct = Math.round((done / total) * 100);
    ringFill.style.strokeDasharray  = `${CIRC}`;
    ringFill.style.strokeDashoffset = `${CIRC * (1 - done / total)}`;
    ringLabel.textContent = `${pct}%`;
    ringSr.textContent = `${total}개 중 ${done}개 완료`;
    ring.classList.toggle('is-complete', done === total);
  }

  /* === 9. 테마 전환 (원형 와이프) ==================================
     View Transitions API가 있으면 클릭 지점에서 원형으로 번집니다. */
  function currentTheme() {
    return root.dataset.theme ||
      (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }

  function setTheme(next) {
    root.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch {}
  }

  function toggleTheme(origin) {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';

    if (!document.startViewTransition || reduceMotion) { setTheme(next); return; }

    root.classList.add('theme-switching');
    const t = document.startViewTransition(() => setTheme(next));

    t.ready.then(() => {
      const x = origin?.x ?? innerWidth - 40;
      const y = origin?.y ?? 30;
      const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));

      root.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
        { duration: 520, easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
          pseudoElement: '::view-transition-new(root)' }
      );
    });

    t.finished.finally(() => root.classList.remove('theme-switching'));
  }

  $('[data-theme-toggle]')?.addEventListener('click', (e) =>
    toggleTheme({ x: e.clientX, y: e.clientY })
  );

  /* === 10. 명령 팔레트 ============================================= */
  const palette      = $('[data-palette]');
  const paletteInput = $('[data-palette-input]');
  const paletteList  = $('[data-palette-list]');
  const paletteEmpty = $('[data-palette-empty]');
  let paletteItems = [];
  let paletteIndex = 0;

  const commands = () => [
    { label: '새 할 일 쓰기',  hint: '/',        run: () => $('#task')?.focus() },
    { label: '전체 보기',      hint: '필터',      run: () => applyFilter('all') },
    { label: '진행 중만 보기',  hint: '필터',      run: () => applyFilter('active') },
    { label: '완료만 보기',     hint: '필터',      run: () => applyFilter('done') },
    { label: '테마 전환',       hint: 'T',        run: () => toggleTheme() },
    { label: '단축키 보기',     hint: '?',        run: () => shortcuts?.showModal() },
  ];

  function renderPalette(q = '') {
    const query = q.trim().toLowerCase();
    const cmds  = commands().filter(c => !query || c.label.toLowerCase().includes(query));
    const tasks = (list ? $$('.task', list) : [])
      .filter(t => !query || t.dataset.task.toLowerCase().includes(query))
      .slice(0, 6)
      .map(t => ({
        label: t.dataset.task,
        hint: t.dataset.done === '1' ? '완료' : '진행 중',
        run: () => { t.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' }); focusTask(t); },
      }));

    paletteItems = [...cmds, ...tasks];
    paletteIndex = 0;
    paletteList.innerHTML = '';

    paletteItems.forEach((item, i) => {
      const li = document.createElement('li');
      li.className = 'palette-item';
      li.setAttribute('role', 'option');
      li.tabIndex = -1;
      li.innerHTML = `<span class="palette-label"></span><span class="palette-hint"></span>`;
      $('.palette-label', li).textContent = item.label;
      $('.palette-hint', li).textContent  = item.hint;
      li.addEventListener('click', () => { palette.close(); item.run(); });
      li.addEventListener('mousemove', () => highlight(i));
      paletteList.append(li);
    });

    paletteEmpty.hidden = paletteItems.length > 0;
    highlight(0);
  }

  function highlight(i) {
    paletteIndex = i;
    $$('.palette-item', paletteList).forEach((li, n) => {
      const on = n === i;
      li.classList.toggle('is-on', on);
      li.setAttribute('aria-selected', String(on));
    });
  }

  function openPalette() {
    if (!palette) return;
    renderPalette('');
    paletteInput.value = '';
    palette.showModal();
    paletteInput.focus();
  }

  $('[data-palette-open]')?.addEventListener('click', openPalette);
  paletteInput?.addEventListener('input', () => renderPalette(paletteInput.value));

  paletteInput?.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); highlight((paletteIndex + 1) % paletteItems.length); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); highlight((paletteIndex - 1 + paletteItems.length) % paletteItems.length); }
    if (e.key === 'Enter')     { e.preventDefault(); const it = paletteItems[paletteIndex]; palette.close(); it?.run(); }
  });

  // 배경을 누르면 닫기
  palette?.addEventListener('click', (e) => { if (e.target === palette) palette.close(); });

  /* === 11. 키보드 단축키 =========================================== */
  const shortcuts = $('[data-shortcuts]');
  $('[data-sheet-close]')?.addEventListener('click', () => shortcuts?.close());
  shortcuts?.addEventListener('click', (e) => { if (e.target === shortcuts) shortcuts.close(); });

  let focused = null;

  function focusTask(task) {
    focused?.classList.remove('is-focused');
    focused = task;
    task?.classList.add('is-focused');
    task?.scrollIntoView({ block: 'nearest' });
  }

  function moveFocus(step) {
    const tasks = $$('.task:not(.is-hidden)', list || document);
    if (!tasks.length) return;
    const at = focused ? tasks.indexOf(focused) : -1;
    focusTask(tasks[Math.max(0, Math.min(tasks.length - 1, at + step))] || tasks[0]);
  }

  const typing = (el) =>
    el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);

  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd+K — 어디서든 팔레트
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      palette?.open ? palette.close() : openPalette();
      return;
    }

    // Ctrl/Cmd+Enter — 입력창에서 바로 추가
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && e.target.id === 'task') {
      e.preventDefault();
      addForm?.requestSubmit();
      return;
    }

    if (typing(e.target) || e.altKey || e.ctrlKey || e.metaKey) return;

    switch (e.key) {
      case '/':
        e.preventDefault();
        $('#task')?.focus();
        break;
      case '?':
        e.preventDefault();
        shortcuts?.showModal();
        break;
      case 'j': case 'J':
        e.preventDefault(); moveFocus(1); break;
      case 'k': case 'K':
        e.preventDefault(); moveFocus(-1); break;
      case 'x': case 'X':
        if (focused) { e.preventDefault(); toggleDone(focused); }
        break;
      case 'e': case 'E':
        if (focused) { e.preventDefault(); startRename(focused); }
        break;
      case 't': case 'T':
        e.preventDefault(); toggleTheme(); break;
      case 'Escape':
        focused?.classList.remove('is-focused');
        focused = null;
        break;
    }
  });

  /* === 목록 이벤트 위임 ============================================
     항목이 새로 생겨도 핸들러를 다시 붙일 필요가 없습니다. */
  list?.addEventListener('submit', (e) => {
    const toggleForm = e.target.closest('[data-toggle-form]');
    if (toggleForm) {
      e.preventDefault();
      toggleDone(toggleForm.closest('.task'));
      return;
    }

    const deleteForm = e.target.closest('[data-delete-form]');
    if (deleteForm) {
      e.preventDefault();
      removeTask(deleteForm.closest('.task'));   // 확인창 대신 실행 취소 토스트
    }
  });

  list?.addEventListener('click', (e) => {
    const text = e.target.closest('[data-text]');
    if (text && !text.isContentEditable) {
      focusTask(text.closest('.task'));
      startRename(text.closest('.task'));
    }
  });

  list?.addEventListener('keydown', (e) => {
    const text = e.target.closest('[data-text]');
    if (text && !text.isContentEditable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      startRename(text.closest('.task'));
    }
  });

  /* === 초기화 ====================================================== */
  // JS가 살아있음을 표시. 삭제 폼의 inline onsubmit이 이 클래스를 보고
  // 확인창을 건너뜁니다 — 동기화로 새로 들어온 행에도 그대로 적용됩니다.
  root.classList.add('js-on');

  // 입력창 높이 자동 조절
  const field = $('#task');
  field?.addEventListener('input', () => {
    field.style.height = 'auto';
    field.style.height = `${Math.min(field.scrollHeight, 260)}px`;
  });

  updateProgress();
})();
