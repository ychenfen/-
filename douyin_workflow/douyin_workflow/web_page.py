"""手机浏览器用的单页：粘贴抖音链接 → 轮询 /transcribe → 显示逐字稿并一键复制。

所有请求用相对路径，所以挂在 nginx 的任意前缀（如 /dy/）下都能用。
访问密码就是服务端的 DOUYIN_SERVER_TOKEN，只存在本机浏览器 localStorage。
"""

INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>抖音转文字</title>
<style>
  :root { --bg:#f6f6f4; --card:#fff; --fg:#1d1d1f; --muted:#6e6e73; --line:#dcdcd8; --accent:#1f5eff; --err:#c0392b; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#111113; --card:#1c1c1f; --fg:#f2f2f2; --muted:#9a9aa0; --line:#333338; --accent:#6b93ff; --err:#ff6b5e; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 -apple-system, "PingFang SC", "Helvetica Neue", sans-serif; }
  main { max-width:680px; margin:0 auto; padding:20px 16px 48px; }
  h1 { font-size:22px; margin:8px 0 16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; margin-bottom:14px; }
  label { display:block; font-size:14px; color:var(--muted); margin-bottom:6px; }
  input, textarea { width:100%; font:inherit; color:var(--fg); background:transparent; border:1px solid var(--line); border-radius:8px; padding:10px; }
  textarea { min-height:96px; resize:vertical; }
  button { font:inherit; border:0; border-radius:8px; padding:11px 16px; cursor:pointer; }
  .primary { background:var(--accent); color:#fff; width:100%; margin-top:12px; font-weight:600; }
  .primary:disabled { opacity:.55; }
  .ghost { background:transparent; color:var(--accent); border:1px solid var(--line); }
  .row { display:flex; gap:8px; margin-top:12px; }
  #status { font-size:14px; color:var(--muted); min-height:1.6em; margin:4px 2px 12px; }
  #status.err { color:var(--err); }
  #out { white-space:pre-wrap; word-break:break-word; }
  .hidden { display:none; }
</style>
</head>
<body>
<main>
  <h1>抖音转文字</h1>
  <div class="card" id="pwCard">
    <label for="pw">访问密码</label>
    <input id="pw" type="password" autocomplete="current-password" placeholder="第一次使用时填写，之后自动记住">
  </div>
  <div class="card">
    <label for="link">粘贴抖音分享口令或链接</label>
    <textarea id="link" placeholder="例如：7.43 复制打开抖音，看看… https://v.douyin.com/xxxx/"></textarea>
    <button class="primary" id="go">转文字</button>
  </div>
  <div id="status"></div>
  <div class="card hidden" id="result">
    <div id="out"></div>
    <div class="row">
      <button class="ghost" id="copy">复制全文</button>
      <button class="ghost" id="again">再转一条</button>
    </div>
  </div>
</main>
<script>
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var KEY = "dy2text_token";
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved) { $("pw").value = saved; $("pwCard").classList.add("hidden"); }

  function status(msg, isErr) { $("status").textContent = msg || ""; $("status").className = isErr ? "err" : ""; }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  async function run() {
    var token = $("pw").value.trim();
    var text = $("link").value.trim();
    if (!token) { $("pwCard").classList.remove("hidden"); status("请先填写访问密码", true); return; }
    if (!text) { status("请粘贴抖音链接", true); return; }
    $("go").disabled = true; $("result").classList.add("hidden");
    status("已提交，正在解析链接…");
    var deadline = Date.now() + 15 * 60 * 1000;
    try {
      while (Date.now() < deadline) {
        var resp = await fetch("transcribe", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
          body: JSON.stringify({ text: text })
        });
        if (resp.status === 401) {
          try { localStorage.removeItem(KEY); } catch (e) {}
          $("pwCard").classList.remove("hidden");
          status("访问密码不对，请重新填写", true); return;
        }
        var data = await resp.json();
        if (data.status === "done") {
          try { localStorage.setItem(KEY, token); } catch (e) {}
          $("pwCard").classList.add("hidden");
          $("out").textContent = data.text;
          $("result").classList.remove("hidden");
          status(data.cached ? "完成（之前转过，直接读取）" : "完成");
          return;
        }
        if (data.status === "error") { status(data.text, true); return; }
        try { localStorage.setItem(KEY, token); } catch (e) {}
        status(data.text || "处理中…");
        await sleep(2000);
      }
      status("等待超时，稍后再点一次，已转好的会直接返回", true);
    } catch (e) {
      status("网络出错：" + e.message, true);
    } finally {
      $("go").disabled = false;
    }
  }

  $("go").addEventListener("click", run);
  $("copy").addEventListener("click", async function () {
    var t = $("out").textContent;
    try { await navigator.clipboard.writeText(t); status("已复制到剪贴板"); }
    catch (e) {
      var r = document.createRange(); r.selectNodeContents($("out"));
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      status("已选中全文，长按选择“拷贝”");
    }
  });
  $("again").addEventListener("click", function () {
    $("link").value = ""; $("result").classList.add("hidden"); status(""); $("link").focus();
  });
})();
</script>
</body>
</html>
"""
