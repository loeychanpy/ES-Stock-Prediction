/**
 * Guided Tour (Panduan) - Dashboard Analisis Saham
 * Animated step-by-step walkthrough of how to obtain the rule-based trading
 * inference. Built on Driver.js 1.3.1 (loaded from CDN in dashboard.html).
 * Bilingual: Bahasa Indonesia (default) / English, toggled inside the popover.
 */
(function () {
  "use strict";

  var LANG_KEY = "es_tour_lang";
  var SEEN_KEY = "es_tour_seen";

  // ---------- Safe localStorage helpers ----------
  function store(key, value) {
    try {
      if (value === undefined) return window.localStorage.getItem(key);
      window.localStorage.setItem(key, value);
    } catch (e) { /* storage blocked: ignore */ }
    return null;
  }

  function getLang() {
    var l = store(LANG_KEY);
    return l === "en" ? "en" : "id";
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = String(s == null ? "" : s);
    return div.innerHTML;
  }

  // ---------- UI labels ----------
  var LABELS = {
    id: { next: "Lanjut &rarr;", prev: "&larr; Kembali", done: "Selesai", progress: "{{current}} / {{total}}" },
    en: { next: "Next &rarr;", prev: "&larr; Back", done: "Done", progress: "{{current}} / {{total}}" }
  };

  // ---------- Tour content ----------
  function buildRawSteps() {
    var decisionEl = document.getElementById("tour-decision");
    var decision = decisionEl ? decisionEl.getAttribute("data-decision") || "TAHAN" : "TAHAN";
    var ticker = decisionEl ? decisionEl.getAttribute("data-ticker") || "" : "";
    var dec = '<b class="tour-dec-' + (decision === "BELI" ? "buy" : "hold") + '">' + escapeHtml(decision) + "</b>";
    var tk = "<b>" + escapeHtml(ticker) + "</b>";

    return [
      {
        el: null,
        title: { id: "Selamat datang 👋", en: "Welcome 👋" },
        body: {
          id: "Panduan singkat ini menunjukkan cara mendapatkan <b>rekomendasi trading</b> dari Sistem Pakar <b>Pure Rule-Based</b> (Forward Chaining, aturan R1&ndash;R10). Ikuti langkahnya satu per satu.",
          en: "This short tour shows how to get a <b>trading recommendation</b> from the <b>pure rule-based</b> Expert System (Forward Chaining, rules R1&ndash;R10). Follow along step by step."
        }
      },
      {
        el: "#liveStatusStrip", side: "bottom",
        title: { id: "Status pasar & data", en: "Market & data status" },
        body: {
          id: "Sesi bursa saat ini (Pra-pembukaan, Sesi 1, Istirahat, Sesi 2, Tutup) dengan jam WIB dan hitung mundur ke event berikutnya. <b>Bar terakhir</b> menunjukkan tanggal candle terbaru: <b class='text-warning'>INTRADAY</b> = pasar masih buka, rekomendasi bisa berubah; <b class='text-success'>EOD</b> = final setelah 16:30 WIB. Data diunduh otomatis tiap 15 menit dan halaman memuat ulang sendiri. Klik <b>Perbarui</b> untuk mengunduh sekarang.",
          en: "The current market session (pre-opening, session 1, break, session 2, closed) with WIB time and a countdown to the next event. <b>Bar terakhir</b> is the latest candle date: <b class='text-warning'>INTRADAY</b> = market still open, the recommendation can change; <b class='text-success'>EOD</b> = final after 16:30 WIB. Data is fetched automatically every 15 minutes and the page reloads itself. Click <b>Perbarui</b> to fetch now."
        }
      },
      {
        el: "#tour-ticker", side: "bottom",
        title: { id: "1. Pilih saham", en: "1. Choose a stock" },
        body: {
          id: "Pilih kode saham BEI di sini, lalu klik <b>Jalankan</b>. Sistem menjalankan inferensi untuk saham tersebut.",
          en: "Pick an IDX stock code here, then click <b>Jalankan</b> (Run). The system runs the inference for that stock."
        }
      },
      {
        el: "#tour-add-stock", side: "bottom",
        title: { id: "Tambah saham baru", en: "Add a new stock" },
        body: {
          id: "Saham belum ada di daftar? Klik <b>Saham Baru</b>, ketik 4 huruf kodenya (mis. ASII). Sistem menambahkan akhiran <code>.JK</code>, mengunduh data 3 tahun dari Yahoo Finance, menghitung semua indikator, dan ikut memperbaruinya otomatis.",
          en: "Stock not in the list? Click <b>Saham Baru</b> and type its 4-letter code (e.g. ASII). The system adds the <code>.JK</code> suffix, downloads 3 years of data from Yahoo Finance, computes every indicator and keeps it updated automatically."
        }
      },
      {
        el: "#tour-params", side: "bottom",
        title: { id: "2. Atur parameter", en: "2. Set the parameters" },
        body: {
          id: "<b>N-Hari Min Low</b> (default 5): berapa candle ke belakang untuk mencari harga terendah. <b>Toleransi</b> (default 3%): seberapa dekat (&plusmn;) Close harus berada dari harga terendah itu. <b>TP</b> / <b>SL</b>: pengali ATR untuk target laba (default 2&times;) dan batas rugi (default 1&times;). Klik <b>Jalankan</b> untuk menghitung ulang; parameter tetap terbawa saat halaman memuat ulang.",
          en: "<b>N-Hari Min Low</b> (default 5): how many candles back to look for the lowest price. <b>Toleransi</b> (default 3%): how close (&plusmn;) the Close must be to that low. <b>TP</b> / <b>SL</b>: ATR multipliers for the profit target (default 2&times;) and stop loss (default 1&times;). Click <b>Jalankan</b> to recalculate; parameters are kept when the page reloads."
        }
      },
      {
        el: ".param-help-toggle", side: "top",
        title: { id: "Panduan parameter", en: "Parameter guide" },
        body: {
          id: "Bingung memilih angka? Buka panel ini untuk penjelasan NPMM, toleransi dua arah, TP/SL, setelan tiap indikator, dan <b>akibat tiap nilai</b> (mis. toleransi 2&ndash;3% direkomendasikan; di atas 3% sinyal bertambah tetapi win rate turun).",
          en: "Not sure which numbers to pick? Open this panel for NPMM, two-sided tolerance, TP/SL, each indicator's settings and <b>what each value does</b> (e.g. 2&ndash;3% tolerance is recommended; above 3% gives more signals but a lower win rate)."
        }
      },
      {
        el: "#tour-price", side: "bottom",
        title: { id: "Harga terakhir", en: "Latest price" },
        body: {
          id: "Harga penutupan terakhir dan perubahan dari hari sebelumnya.",
          en: "The latest close and the change from the previous day."
        }
      },
      {
        el: "#tour-decision", side: "right",
        title: { id: "3. Rekomendasi akhir", en: "3. Final recommendation" },
        body: {
          id: "Inilah hasil utama: <b>BELI</b> atau <b>TAHAN</b>. BELI hanya muncul jika ada aturan beli yang terpicu, <b>tidak ada</b> aturan TAHAN yang terpicu, dan filter validasi lolos.",
          en: "This is the main output: <b>BELI</b> (buy) or <b>TAHAN</b> (hold). BUY only appears when a buy rule fired, <b>no</b> HOLD rule fired, and the validation filter passes."
        }
      },
      {
        el: "#tour-rules", side: "right",
        title: { id: "Aturan yang terpicu", en: "Rules fired" },
        body: {
          id: "<b>R1&ndash;R5</b> adalah aturan BELI, <b>R6&ndash;R10</b> aturan TAHAN. Jika keduanya terpicu bersamaan, sistem memilih TAHAN (konservatif).",
          en: "<b>R1&ndash;R5</b> are BUY rules and <b>R6&ndash;R10</b> are HOLD rules. If both fire on the same day, the system picks HOLD (conservative)."
        }
      },
      {
        el: "#tour-filter", side: "right",
        title: { id: "Filter validasi (Tahap 3)", en: "Validation filter (Stage 3)" },
        body: {
          id: "Dua syarat wajib: <b>tren naik</b> (SMA20 &gt; SMA50) dan Close berada dalam <b>&plusmn;toleransi</b> dari Low terendah N candle sebelumnya. Jika salah satu <span class='text-danger'>Gagal</span>, keputusan dipaksa TAHAN.",
          en: "Two required conditions: an <b>uptrend</b> (SMA20 &gt; SMA50) and the Close within <b>&plusmn;tolerance</b> of the lowest Low of the previous N candles. If either shows <span class='text-danger'>Gagal</span> (failed), the decision is forced to HOLD."
        }
      },
      {
        el: "#tour-targets", side: "top",
        title: { id: "4. Entry, TP & SL", en: "4. Entry, TP & SL" },
        body: {
          id: "Jika BELI, gunakan harga ini sebagai acuan: <b>Entry</b> (Close terakhir), <b class='text-success'>Take Profit</b> = Entry + TP&times;ATR, <b class='text-danger'>Stop Loss</b> = Entry &minus; SL&times;ATR. Sistem tidak memantau posisi Anda; pantau TP/SL sendiri.",
          en: "On a BUY, use these as reference levels: <b>Entry</b> (latest Close), <b class='text-success'>Take Profit</b> = Entry + TP&times;ATR, <b class='text-danger'>Stop Loss</b> = Entry &minus; SL&times;ATR. The system does not track your position; watch TP/SL yourself."
        }
      },
      {
        el: "#tour-facts", side: "bottom",
        title: { id: "5. Fakta & pemicu indikator", en: "5. Indicator facts & triggers" },
        body: {
          id: "Nilai <b>RSI</b>, <b>MACD Histogram</b>, dan <b>%B</b> hari ini dibanding kemarin. Aturan terpicu saat garis acuan <b>disentuh atau dilewati</b>: RSI 30/70, MACD 0, %B 0/0,5/1.",
          en: "Today's <b>RSI</b>, <b>MACD Histogram</b> and <b>%B</b> versus yesterday. A rule fires when a reference line is <b>touched or crossed</b>: RSI 30/70, MACD 0, %B 0/0.5/1."
        }
      },
      {
        el: "#tour-risk", side: "top",
        title: { id: "Risiko & tren", en: "Risk & trend" },
        body: {
          id: "<b>ATR</b> mengukur volatilitas (dasar TP/SL), <b>SMA20/50</b> menentukan tren, dan <b>Minimum Lokal</b> dipakai untuk filter jarak &plusmn;toleransi.",
          en: "<b>ATR</b> measures volatility (basis for TP/SL), <b>SMA20/50</b> define the trend, and the <b>Local Minimum</b> is used for the &plusmn;tolerance distance filter."
        }
      },
      {
        el: "#tour-explanation", side: "top",
        title: { id: "6. Penjelasan penalaran", en: "6. Reasoning explanation" },
        body: {
          id: "Narasi otomatis yang menjelaskan <b>mengapa</b> sistem memberi rekomendasi tersebut. Baca bagian ini untuk memahami hasilnya.",
          en: "An automatic narrative explaining <b>why</b> the system gave this recommendation. Read it to understand the result."
        }
      },
      {
        el: "#tour-chart", side: "top",
        title: { id: "Grafik TradingView", en: "TradingView chart" },
        body: {
          id: "Pilih timeframe <b>1D / 1W / 1M</b> (1 candle = 1 hari / minggu / bulan) dan rentang zoom (1 Bulan &ndash; Semua Data). Ada 5 panel: candle + SMA20/50 + penanda sinyal BELI, <b>%B</b>, <b>RSI</b>, <b>MACD</b>, dan <b>ATR</b>. <b>Scroll</b> untuk zoom, <b>geser</b> untuk melihat history, klik dua kali sumbu harga untuk reset. Timeframe hanya mengubah grafik; <b>rekomendasi tetap dari data harian</b>.",
          en: "Pick the <b>1D / 1W / 1M</b> timeframe (1 candle = 1 day / week / month) and a zoom range (1 month &ndash; all data). There are 5 panes: candles + SMA20/50 + BUY signal markers, <b>%B</b>, <b>RSI</b>, <b>MACD</b> and <b>ATR</b>. <b>Scroll</b> to zoom, <b>drag</b> to browse history, double-click the price axis to reset. The timeframe only changes the chart; <b>the recommendation always uses daily data</b>."
        }
      },
      {
        el: "#tour-history", side: "top",
        title: { id: "Track record sinyal", en: "Signal track record" },
        body: {
          id: "Semua sinyal <b>BELI</b> yang pernah terpicu dengan parameter aktif: tanggal, harga, aturan, nilai indikator, TP/SL, dan jarak ke minimum lokal. Berguna untuk melihat seberapa sering dan di mana sistem memberi sinyal.",
          en: "Every past <b>BUY</b> signal under the current parameters: date, price, rules, indicator values, TP/SL and distance to the local minimum. Useful to see how often and where the system signals."
        }
      },
      {
        el: "#tour-kb", side: "top",
        title: { id: "Basis aturan R1–R10", en: "Knowledge base R1–R10" },
        body: {
          id: "Daftar lengkap aturan IF&ndash;THEN. Kartu yang menyala adalah aturan yang <b>TERPICU</b> hari ini beserta makna setiap aturan.",
          en: "The full list of IF&ndash;THEN rules. Highlighted cards are the rules that <b>FIRED</b> today, along with what each rule means."
        }
      },
      {
        el: null,
        title: { id: "Selesai! 🎉", en: "All done! 🎉" },
        body: {
          id: "Rekomendasi hari ini untuk " + tk + ": " + dec + ".<br>Ingin menguji strategi ini di masa lalu? Buka menu <b>Backtest &amp; Evaluasi</b> (masuk H+1 di harga Open, keluar di TP/SL). Klik <b>Panduan</b> kapan saja untuk mengulang tur ini.",
          en: "Today's recommendation for " + tk + ": " + dec + ".<br>Want to test this strategy on past data? Open <b>Backtest &amp; Evaluasi</b> (entry at next-day Open, exit at TP/SL). Click <b>Panduan</b> any time to replay this tour."
        }
      }
    ];
  }

  function buildSteps(lang) {
    return buildRawSteps()
      .filter(function (s) { return !s.el || document.querySelector(s.el); })
      .map(function (s) {
        var step = { popover: { title: s.title[lang], description: s.body[lang] } };
        if (s.el) {
          step.element = s.el;
          step.popover.side = s.side || "bottom";
          step.popover.align = "start";
        }
        return step;
      });
  }

  // ---------- Driver setup ----------
  var driverObj = null;

  function start(index) {
    if (!window.driver || !window.driver.js) {
      console.warn("Driver.js failed to load; guided tour unavailable.");
      return;
    }
    var lang = getLang();
    var L = LABELS[lang];

    driverObj = window.driver.js.driver({
      steps: buildSteps(lang),
      animate: true,
      smoothScroll: true,
      allowClose: true,
      showProgress: true,
      progressText: L.progress,
      nextBtnText: L.next,
      prevBtnText: L.prev,
      doneBtnText: L.done,
      overlayOpacity: 0.7,
      stagePadding: 6,
      stageRadius: 10,
      popoverClass: "es-tour-popover",
      onPopoverRender: function (popover) {
        var toggle = document.createElement("div");
        toggle.className = "es-tour-lang";
        ["id", "en"].forEach(function (code) {
          var b = document.createElement("button");
          b.type = "button";
          b.textContent = code.toUpperCase();
          if (code === lang) b.classList.add("active");
          b.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (code === getLang()) return;
            var idx = driverObj.getActiveIndex() || 0;
            store(LANG_KEY, code);
            driverObj.destroy();
            start(idx);
          });
          toggle.appendChild(b);
        });
        popover.footer.insertBefore(toggle, popover.footer.firstChild);
      },
      onDestroyed: function () {
        store(SEEN_KEY, "1");
      }
    });

    driverObj.drive(index || 0);
  }

  // ---------- Init ----------
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("btnStartTour");
    if (btn) btn.addEventListener("click", function () { start(0); });

    // Auto-start once for first-time visitors
    if (store(SEEN_KEY) !== "1") {
      setTimeout(function () { start(0); }, 600);
    }
  });
})();
