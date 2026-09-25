"""手机浏览器用的单页：抖音分享链接 → 转写 → 校对、复制或下载。

请求使用相对路径，因此挂在 nginx 前缀（如 /dy/）下也能工作。
访问密码只保存在当前浏览器的 localStorage。
"""

INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#f3efe5">
<link rel="icon" href="data:,">
<title>抖音素材台</title>
<style>
  :root {
    --paper:#f3efe5; --card:#fffdf7; --ink:#17211f; --muted:#65706d;
    --line:#d7d2c4; --accent:#006d62; --accent-deep:#004c45; --soft:#dfece7;
    --warn:#b33a2f; --shadow:0 14px 40px rgba(43,53,47,.08);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper:#151a19; --card:#1d2422; --ink:#f2eee3; --muted:#a8b1ad;
      --line:#39413e; --accent:#74d8c6; --accent-deep:#a4ebdf; --soft:#263b36;
      --warn:#ff8e82; --shadow:0 16px 42px rgba(0,0,0,.24);
    }
  }
  * { box-sizing:border-box; }
  html { -webkit-text-size-adjust:100%; }
  body {
    margin:0; min-height:100vh; color:var(--ink); background:var(--paper);
    font:16px/1.6 "Avenir Next", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  }
  body::before {
    content:""; position:fixed; inset:0; pointer-events:none; opacity:.25;
    background-image:radial-gradient(circle at 15% 0%, rgba(0,109,98,.16), transparent 32%),
      repeating-linear-gradient(90deg, transparent 0 31px, rgba(65,70,62,.025) 31px 32px);
  }
  button, input, textarea { font:inherit; }
  button { touch-action:manipulation; }
  main { position:relative; width:min(100%, 760px); margin:auto; padding:24px 16px calc(56px + env(safe-area-inset-bottom)); }
  header { display:flex; align-items:flex-end; justify-content:space-between; gap:20px; margin:4px 2px 22px; }
  .eyebrow { margin:0 0 2px; color:var(--accent); font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
  h1 { margin:0; font:700 clamp(28px, 8vw, 46px)/1.08 "Songti SC", "STSong", serif; letter-spacing:-.04em; }
  .edition { color:var(--muted); font-size:12px; white-space:nowrap; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:18px; margin-bottom:14px; box-shadow:var(--shadow); }
  .card-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:12px; }
  .card h2 { margin:0; font-size:16px; letter-spacing:.01em; }
  .step-no { display:inline-grid; place-items:center; width:26px; height:26px; margin-right:8px; border:1px solid var(--accent); border-radius:50%; color:var(--accent); font-size:12px; }
  label { display:block; margin:0 0 7px; color:var(--muted); font-size:13px; font-weight:650; }
  input, textarea {
    width:100%; color:var(--ink); background:rgba(255,255,255,.18); border:1px solid var(--line);
    border-radius:12px; padding:12px 13px; outline:none; transition:border-color .16s, box-shadow .16s;
  }
  input:focus, textarea:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(0,109,98,.12); }
  #link { min-height:118px; resize:vertical; }
  #transcript { min-height:300px; resize:vertical; line-height:1.8; }
  .hint { margin:8px 2px 0; color:var(--muted); font-size:12px; }
  .primary, .action, .text-btn {
    border:0; border-radius:12px; cursor:pointer; min-height:46px; font-weight:720;
  }
  .primary { width:100%; margin-top:14px; color:#fff; background:var(--accent-deep); letter-spacing:.04em; }
  @media (prefers-color-scheme:dark) { .primary { color:#082a25; } }
  .primary:disabled { cursor:wait; opacity:.55; }
  .actions { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:9px; margin-top:14px; }
  .action { color:var(--accent-deep); background:var(--soft); padding:10px 9px; font-size:14px; }
  .action.strong { color:#fff; background:var(--accent-deep); }
  @media (prefers-color-scheme:dark) { .action.strong { color:#082a25; } }
  .text-btn { min-height:auto; padding:3px; color:var(--accent); background:transparent; font-size:13px; }
  #statusBox { min-height:0; overflow:hidden; transition:max-height .2s, opacity .2s; }
  #statusBox.hidden { display:block; max-height:0; opacity:0; margin:0; padding:0 18px; border-width:0; }
  #statusBox:not(.hidden) { max-height:160px; opacity:1; }
  #status { margin:10px 0 0; color:var(--muted); font-size:13px; }
  #status.err { color:var(--warn); }
  .stages { display:grid; grid-template-columns:repeat(3, 1fr); gap:5px; list-style:none; padding:0; margin:0; }
  .stages li { position:relative; padding-top:8px; color:var(--muted); font-size:11px; text-align:center; }
  .stages li::before { content:""; position:absolute; inset:0 2px auto; height:3px; border-radius:4px; background:var(--line); }
  .stages li.on, .stages li.done { color:var(--accent-deep); font-weight:700; }
  .stages li.on::before, .stages li.done::before { background:var(--accent); }
  .stages li.on::before { animation:pulse 1.3s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity:.35; } }
  .result-head { align-items:flex-start; }
  .result-title { margin:0; font:700 22px/1.3 "Songti SC", "STSong", serif; }
  .meta { margin:5px 0 0; color:var(--muted); font-size:13px; }
  .cache-tag { flex:none; padding:4px 8px; color:var(--accent-deep); background:var(--soft); border-radius:999px; font-size:11px; font-weight:700; }
  .edit-label { display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin-top:18px; }
  .edit-label small { font-weight:400; }
  .full { grid-column:1 / -1; }
  .history-list { display:grid; gap:8px; margin:0; padding:0; list-style:none; }
  .history-list li { display:grid; grid-template-columns:1fr auto; gap:6px 12px; padding:10px 0; border-top:1px solid var(--line); }
  .history-list li:first-child { border-top:0; }
  .history-title { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; font-weight:700; }
  .history-time, .history-meta { color:var(--muted); font-size:11px; }
  .history-meta { grid-column:1 / -1; }
  .hidden { display:none !important; }
  .toast { position:fixed; z-index:5; left:50%; bottom:calc(24px + env(safe-area-inset-bottom)); transform:translate(-50%, 18px); max-width:calc(100% - 32px); padding:10px 16px; color:#fff; background:#17211f; border-radius:999px; opacity:0; pointer-events:none; transition:.2s; font-size:13px; box-shadow:0 8px 24px rgba(0,0,0,.18); }
  .toast.show { opacity:1; transform:translate(-50%, 0); }
  @media (max-width:380px) { .actions { grid-template-columns:1fr; } .full { grid-column:auto; } }
</style>
</head>
<body>
<main>
  <header>
    <div><p class="eyebrow">Video Research Desk</p><h1>抖音素材台</h1></div>
    <span class="edition">私人工具 · 网页版</span>
  </header>

  <section class="card" id="pwCard">
    <div class="card-head"><h2><span class="step-no">0</span>访问验证</h2></div>
    <label for="pw">访问密码</label>
    <input id="pw" type="password" autocomplete="current-password" placeholder="只保存在这台设备的浏览器里">
  </section>

  <section class="card">
    <div class="card-head"><h2><span class="step-no">1</span>放入素材</h2><button class="text-btn hidden" id="forget" type="button">更换密码</button></div>
    <label for="link">抖音分享口令或链接</label>
    <textarea id="link" placeholder="粘贴整段分享口令即可，系统会自动识别其中的链接"></textarea>
    <p class="hint">支持 v.douyin.com 短链；首次处理长视频可能需要几分钟。</p>
    <button class="primary" id="go" type="button">开始提取文字</button>
  </section>

  <section class="card hidden" id="statusBox" aria-live="polite">
    <ol class="stages" id="stages">
      <li>解析链接</li><li>下载并转写</li><li>整理完成</li>
    </ol>
    <p id="status"></p>
  </section>

  <section class="card hidden" id="result">
    <div class="card-head result-head">
      <div><p class="eyebrow">Transcript</p><h2 class="result-title" id="resultTitle"></h2><p class="meta" id="resultMeta"></p></div>
      <span class="cache-tag hidden" id="cacheTag">缓存秒回</span>
    </div>
    <label class="edit-label" for="transcript"><span>逐字稿</span><small>可直接修正人名、产品名和错别字</small></label>
    <textarea id="transcript" spellcheck="false"></textarea>
    <div class="actions">
      <button class="action strong" id="copyTranscript" type="button">复制纯逐字稿</button>
      <button class="action" id="copyFull" type="button">复制完整信息</button>
      <button class="action" id="download" type="button">下载 TXT</button>
      <button class="action" id="copyResearch" type="button">复制深挖提示词</button>
      <button class="action full" id="again" type="button">继续处理下一条</button>
    </div>
  </section>

  <section class="card hidden" id="historyCard">
    <div class="card-head"><h2><span class="step-no">↺</span>最近处理</h2><button class="text-btn" id="clearHistory" type="button">清空</button></div>
    <ul class="history-list" id="history"></ul>
  </section>
</main>
<div class="toast" id="toast" role="status"></div>
<script>
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var TOKEN_KEY = "dy2text_token";
  var HISTORY_KEY = "dy2text_history_v1";
  var current = null;
  var toastTimer = null;

  function getStored(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch (e) { return fallback; } }
  function setStored(key, value) { try { localStorage.setItem(key, typeof value === "string" ? value : JSON.stringify(value)); } catch (e) {} }
  function removeStored(key) { try { localStorage.removeItem(key); } catch (e) {} }
  function savedToken() { try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; } }
  function sleep(ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); }
  function showToast(message) {
    $("toast").textContent = message; $("toast").classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { $("toast").classList.remove("show"); }, 1800);
  }
  function setStatus(message, isError, stage) {
    $("statusBox").classList.remove("hidden");
    $("status").textContent = message || ""; $("status").className = isError ? "err" : "";
    Array.prototype.forEach.call($("stages").children, function (item, index) {
      item.className = index < stage ? "done" : (index === stage ? "on" : "");
    });
  }
  function hideStatus() { $("statusBox").classList.add("hidden"); }
  function updateAuthUI() {
    var hasToken = !!savedToken();
    if (hasToken) { $("pw").value = savedToken(); $("pwCard").classList.add("hidden"); $("forget").classList.remove("hidden"); }
    else { $("pwCard").classList.remove("hidden"); $("forget").classList.add("hidden"); }
  }
  function cleanFileName(name) { return (name || "抖音逐字稿").replace(/[\\/:*?\"<>|]/g, "-").slice(0, 70); }
  function fullText() {
    var title = current && current.title ? current.title : "（无标题）";
    var meta = [current && current.author, current && current.duration_s ? current.duration_s + " 秒" : ""].filter(Boolean).join(" · ");
    return [title, meta, "", $("transcript").value.trim()].filter(function (x, i) { return x || i === 2; }).join("\n").trim();
  }
  function researchPrompt() {
    return "请把下面这条短视频当作待核查素材，而不是事实来源。先修正 ASR 里可能识别错的人名、产品名、英文缩写和专有名词，再完成深入研究。\n\n" +
      "要求：\n1. 分开列出：视频原话、可验证事实、营销或推测性主张。\n2. 优先查项目官网、官方公告、论文、代码仓库及当事人原始发言；二手报道只作补充。\n3. 对数字、日期、模型名称、开源状态和能力边界逐项核实。\n4. 找不到可靠证据的内容明确写“未核实”，不要补全或猜测。\n5. 最后说明：这条内容对我的工作流有什么可复用的做法、哪些部分不建议照搬，并给出一个最小验证方案。\n6. 附上可点击来源链接，并标明每个来源支持哪项结论。\n\n素材：\n" + fullText();
  }
  async function copyText(text, success) {
    try { await navigator.clipboard.writeText(text); showToast(success); }
    catch (e) {
      var helper = document.createElement("textarea"); helper.value = text; helper.style.position = "fixed"; helper.style.opacity = "0";
      document.body.appendChild(helper); helper.select();
      var ok = false; try { ok = document.execCommand("copy"); } catch (ignore) {}
      document.body.removeChild(helper); showToast(ok ? success : "复制失败，请手动长按选择");
    }
  }
  function saveHistory(data) {
    var rows = getStored(HISTORY_KEY, []).filter(function (x) { return x.aweme_id !== data.aweme_id; });
    rows.unshift({ aweme_id:data.aweme_id, title:data.title || "无标题", author:data.author || "", at:Date.now() });
    setStored(HISTORY_KEY, rows.slice(0, 5)); renderHistory();
  }
  function renderHistory() {
    var rows = getStored(HISTORY_KEY, []); $("history").textContent = "";
    $("historyCard").classList.toggle("hidden", !rows.length);
    rows.forEach(function (row) {
      var item = document.createElement("li");
      var title = document.createElement("span"); title.className = "history-title"; title.textContent = row.title;
      var when = document.createElement("time"); when.className = "history-time"; when.textContent = new Date(row.at).toLocaleDateString("zh-CN", { month:"numeric", day:"numeric" });
      var meta = document.createElement("span"); meta.className = "history-meta"; meta.textContent = [row.author, "ID " + row.aweme_id].filter(Boolean).join(" · ");
      item.appendChild(title); item.appendChild(when); item.appendChild(meta); $("history").appendChild(item);
    });
  }
  function showResult(data) {
    current = data;
    $("resultTitle").textContent = data.title || "（无标题）";
    $("resultMeta").textContent = [data.author, data.duration_s ? data.duration_s + " 秒" : "", data.aweme_id ? "ID " + data.aweme_id : ""].filter(Boolean).join(" · ");
    $("transcript").value = data.transcript || data.text || "";
    $("cacheTag").classList.toggle("hidden", !data.cached);
    $("result").classList.remove("hidden");
    saveHistory(data);
  }
  async function run() {
    var token = $("pw").value.trim(); var text = $("link").value.trim();
    if (!token) { updateAuthUI(); setStatus("请先填写访问密码。", true, 0); $("pw").focus(); return; }
    if (!text) { setStatus("请先粘贴抖音分享口令或链接。", true, 0); $("link").focus(); return; }
    $("go").disabled = true; $("result").classList.add("hidden"); setStatus("正在识别分享链接…", false, 0);
    var deadline = Date.now() + 15 * 60 * 1000;
    try {
      while (Date.now() < deadline) {
        var response = await fetch("transcribe", {
          method:"POST", headers:{ "Content-Type":"application/json", "Authorization":"Bearer " + token }, body:JSON.stringify({ text:text })
        });
        if (response.status === 401) {
          removeStored(TOKEN_KEY); updateAuthUI(); setStatus("访问密码不对，请重新填写。", true, 0); $("pw").focus(); return;
        }
        var data = await response.json();
        if (data.status === "done") {
          setStored(TOKEN_KEY, token); updateAuthUI(); showResult(data); setStatus(data.cached ? "已从缓存读取，可以直接校对和使用。" : "转写完成，可以直接校对和使用。", false, 2); return;
        }
        if (data.status === "error") { setStatus(data.text || "处理失败。", true, 1); return; }
        setStored(TOKEN_KEY, token); updateAuthUI(); setStatus(data.text || "正在下载并转写…", false, 1); await sleep(2000);
      }
      setStatus("本次等待超时。稍后再点一次，完成后会直接从缓存返回。", true, 1);
    } catch (e) { setStatus("网络出错：" + e.message, true, 1); }
    finally { $("go").disabled = false; }
  }

  $("go").addEventListener("click", run);
  $("forget").addEventListener("click", function () { removeStored(TOKEN_KEY); $("pw").value = ""; updateAuthUI(); $("pw").focus(); });
  $("copyTranscript").addEventListener("click", function () { copyText($("transcript").value.trim(), "逐字稿已复制"); });
  $("copyFull").addEventListener("click", function () { copyText(fullText(), "完整信息已复制"); });
  $("copyResearch").addEventListener("click", function () { copyText(researchPrompt(), "深挖提示词已复制"); });
  $("download").addEventListener("click", function () {
    var blob = new Blob([fullText() + "\n"], { type:"text/plain;charset=utf-8" }); var url = URL.createObjectURL(blob);
    var link = document.createElement("a"); link.href = url; link.download = cleanFileName(current && current.title) + ".txt";
    document.body.appendChild(link); link.click(); document.body.removeChild(link); URL.revokeObjectURL(url); showToast("TXT 已下载");
  });
  $("again").addEventListener("click", function () { current = null; $("link").value = ""; $("result").classList.add("hidden"); hideStatus(); window.scrollTo({ top:0, behavior:"smooth" }); $("link").focus(); });
  $("clearHistory").addEventListener("click", function () { removeStored(HISTORY_KEY); renderHistory(); showToast("历史已清空"); });

  updateAuthUI(); renderHistory();
})();
</script>
</body>
</html>
"""
