const API_BASE = "http://localhost:8000/api";

const algorithmCards = document.querySelectorAll(".algorithm-card");

const workspace = document.getElementById("workspace");
const algorithmTitle = document.getElementById("algorithmTitle");
const algorithmDescription = document.getElementById("algorithmDescription");
const roiHint = document.getElementById("roiHint");
const expectedOutputs = document.getElementById("expectedOutputs");

const imageInput = document.getElementById("imageInput");
const imageCanvas = document.getElementById("imageCanvas");
const ctx = imageCanvas.getContext("2d", { willReadFrequently: true });

const statusBox = document.getElementById("statusBox");
const resultContainer = document.getElementById("resultContainer");

const analyzeButton = document.getElementById("analyzeButton");
const clearRoiButton = document.getElementById("clearRoiButton");
const backButton = document.getElementById("backButton");

// 色卡专用参数
const colorCheckerParams = document.getElementById("colorCheckerParams");
const colorSpaceSelect = document.getElementById("colorSpaceSelect");
const whitePointSelect = document.getElementById("whitePointSelect");
const loadRefButton = document.getElementById("loadRefButton");
const uploadRefButton = document.getElementById("uploadRefButton");
const refFileInput = document.getElementById("refFileInput");

let currentAlgorithm = null;
let currentImageFile = null;
let loadedImage = null;
let sourceImageData = null;

let isDrawing = false;
let hasROI = false;
let startX = 0;
let startY = 0;
let currentX = 0;
let currentY = 0;
let lastROI = null;

const algorithmInfo = {
  slantedEdge: {
    name: "ISO 12233 斜边法",
    description: "通过斜边 ROI 计算 ESF、LSF、MTF、MTF50 和 MTF10。",
    roiHint: "选择清晰、高对比度且略微倾斜的边缘。建议倾角为 3°～8°，ROI 至少 100 × 100 px。",
    outputs: ["ESF：边缘扩散函数", "LSF：线扩散函数", "MTF：调制传递函数", "MTF50、MTF10", "边缘角度与 ROI 信息"]
  },
  siemensStar: {
    name: "西门子星图",
    description: "径向 MTF 与分辨率测试。",
    roiHint: "选择星图中心区域，确保包含完整的放射状线条。",
    outputs: ["径向 MTF", "分辨率 (LP/mm)", "角度响应"]
  },
  deadLeaves: {
    name: "枯叶图",
    description: "纹理、降噪、锐化测试。",
    roiHint: "选择枯叶图纹理区域，避免边缘和纯色区域。",
    outputs: ["纹理保留度", "降噪效果", "锐化程度"]
  },
  linePairs: {
    name: "线对",
    description: "分辨率与对比度测试。",
    roiHint: "选择包含清晰线对的区域。",
    outputs: ["分辨率", "对比度", "调制传递"]
  },
  colorChecker: {
    name: "24 色卡",
    description: "色差、白平衡、饱和度测试。自动识别 4x6 色块布局。",
    roiHint: "选择包含完整 24 色卡的区域（4 行 x 6 列）。确保色卡方向正确。",
    outputs: ["XYZ 色度值", "CIELAB", "CIELUV", "色差 ΔE (CIE76)"]
  },
  grayScale: {
    name: "灰阶",
    description: "Gamma 与动态范围测试。",
    roiHint: "选择包含完整灰阶条的区域。",
    outputs: ["Gamma 值", "动态范围", "阶调响应"]
  },
  checkerboard: {
    name: "棋盘格",
    description: "畸变、标定、角点检测。",
    roiHint: "选择完整棋盘格区域，确保角点清晰可见。",
    outputs: ["畸变系数", "角点坐标", "标定参数"]
  },
  uniformity: {
    name: "均匀性",
    description: "亮度、色彩、暗角测试。",
    roiHint: "选择均匀光照的纯色区域。",
    outputs: ["亮度均匀性", "色彩均匀性", "暗角程度"]
  }
};

function setStatus(message) {
  statusBox.innerHTML = message;
}

function resetResult() {
  resultContainer.innerHTML = `
    <p class="empty-text">选择模型、上传图像并框选 ROI 后，分析结果将在此显示。</p>
  `;
}

function renderExpectedOutputs(outputs) {
  expectedOutputs.innerHTML = outputs.map((item) => `<div class="output-item">${item}</div>`).join("");
}

function selectAlgorithm(algorithmId) {
  const info = algorithmInfo[algorithmId];
  if (!info) return;

  currentAlgorithm = algorithmId;

  algorithmCards.forEach((card) => {
    card.classList.toggle("active", card.dataset.algorithm === algorithmId);
  });

  algorithmTitle.textContent = `${info.name}分析工作区`;
  algorithmDescription.textContent = info.description;
  roiHint.textContent = info.roiHint;
  renderExpectedOutputs(info.outputs);

  // 色卡模式特殊处理
  if (algorithmId === "colorChecker") {
    if (colorCheckerParams) colorCheckerParams.style.display = "block";
    roiHint.textContent = "上传图片后，用鼠标拖动框选包含完整 24 色卡的区域（4 行 x 6 列）。确保色卡方向正确。";
  } else {
    if (colorCheckerParams) colorCheckerParams.style.display = "none";
  }

  workspace.classList.remove("hidden");
  setStatus(`<strong>当前模型：</strong>${info.name}<br />请上传图片，然后按要求框选 ROI。`);
  resetResult();
  workspace.scrollIntoView({ behavior: "smooth", block: "start" });
}

function redrawImage() {
  if (!loadedImage) return;
  ctx.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
  ctx.drawImage(loadedImage, 0, 0);
}

function getCanvasPoint(event) {
  const rect = imageCanvas.getBoundingClientRect();
  return {
    x: Math.floor((event.clientX - rect.left) * imageCanvas.width / rect.width),
    y: Math.floor((event.clientY - rect.top) * imageCanvas.height / rect.height)
  };
}

function getROI() {
  const x = Math.max(0, Math.min(startX, currentX));
  const y = Math.max(0, Math.min(startY, currentY));
  const width = Math.min(imageCanvas.width - x, Math.abs(currentX - startX));
  const height = Math.min(imageCanvas.height - y, Math.abs(currentY - startY));
  return { x: Math.floor(x), y: Math.floor(y), width: Math.floor(width), height: Math.floor(height) };
}

function drawROI() {
  redrawImage();
  if (!hasROI && !isDrawing) return;
  const roi = getROI();
  if (roi.width < 1 || roi.height < 1) return;

  ctx.save();
  ctx.fillStyle = "rgba(37, 99, 235, 0.16)";
  ctx.fillRect(roi.x, roi.y, roi.width, roi.height);
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2;
  ctx.setLineDash([8, 4]);
  ctx.strokeRect(roi.x, roi.y, roi.width, roi.height);
  ctx.restore();

  // 色卡模式：叠加 24 个子色块（4 行 x 6 列）网格并标注编号
  if (currentAlgorithm === "colorChecker") {
    drawColorCheckerGrid(roi);
  }
}

/**
 * 在 ROI 上绘制 4x6 的 24 色块网格，并标注编号 1-24
 * 每个小 ROI 向内缩进 insetRatio，避免压到色块之间的边界
 */
function drawColorCheckerGrid(roi) {
  const rows = 4, cols = 6;
  const cellW = roi.width / cols;
  const cellH = roi.height / rows;
  const insetRatio = 0.18; // 每个子 ROI 向内缩进比例（避免边界）

  ctx.save();
  ctx.setLineDash([]);

  // 外层整体网格线（淡）
  ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
  ctx.lineWidth = 1;
  for (let r = 0; r <= rows; r++) {
    const y = roi.y + r * cellH;
    ctx.beginPath();
    ctx.moveTo(roi.x, y);
    ctx.lineTo(roi.x + roi.width, y);
    ctx.stroke();
  }
  for (let c = 0; c <= cols; c++) {
    const x = roi.x + c * cellW;
    ctx.beginPath();
    ctx.moveTo(x, roi.y);
    ctx.lineTo(x, roi.y + roi.height);
    ctx.stroke();
  }

  // 编号 1-24（按行优先：row 0 -> 1..6, row 1 -> 7..12 ...）
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "rgba(0, 0, 0, 0.7)";
  ctx.lineWidth = 3;
  ctx.font = "bold 14px Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  let idx = 1;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cx = roi.x + c * cellW + cellW / 2;
      const cy = roi.y + r * cellH + cellH / 2;

      // 每个子 ROI 向内缩进，画一个明显的方框
      const ix = roi.x + c * cellW + cellW * insetRatio;
      const iy = roi.y + r * cellH + cellH * insetRatio;
      const iw = cellW * (1 - 2 * insetRatio);
      const ih = cellH * (1 - 2 * insetRatio);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(ix, iy, iw, ih);

      // 编号
      ctx.strokeText(String(idx), cx, cy);
      ctx.fillText(String(idx), cx, cy);
      idx++;
    }
  }
  ctx.restore();
}

function clearROI() {
  hasROI = false;
  isDrawing = false;
  redrawImage();
  analyzeButton.disabled = true;
  setStatus(`<strong>当前状态：</strong>ROI 已清除，请重新选择测试区域。`);
  resetResult();
}

algorithmCards.forEach((card) => {
  card.addEventListener("click", () => selectAlgorithm(card.dataset.algorithm));
});

imageInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) return;

  currentImageFile = file;

  const reader = new FileReader();
  reader.onload = (loadEvent) => {
    loadedImage = new Image();
    loadedImage.onload = () => {
      imageCanvas.width = loadedImage.naturalWidth;
      imageCanvas.height = loadedImage.naturalHeight;
      redrawImage();
      sourceImageData = ctx.getImageData(0, 0, imageCanvas.width, imageCanvas.height);
      hasROI = false;
      clearRoiButton.disabled = false;
      analyzeButton.disabled = true;
      setStatus(`<strong>图片已加载：</strong>${imageCanvas.width} × ${imageCanvas.height} px。<br />请按当前模型要求拖动鼠标框选 ROI。`);
      resetResult();
    };
    loadedImage.src = loadEvent.target.result;
  };
  reader.readAsDataURL(file);
});

imageCanvas.addEventListener("mousedown", (event) => {
  if (!loadedImage) return;
  const point = getCanvasPoint(event);
  isDrawing = true;
  hasROI = false;
  startX = point.x;
  startY = point.y;
  currentX = point.x;
  currentY = point.y;
});

imageCanvas.addEventListener("mousemove", (event) => {
  if (!isDrawing || !loadedImage) return;
  const point = getCanvasPoint(event);
  currentX = point.x;
  currentY = point.y;
  drawROI();
});

window.addEventListener("mouseup", (event) => {
  if (!isDrawing || !loadedImage) return;
  isDrawing = false;
  const point = getCanvasPoint(event);
  currentX = Math.max(0, Math.min(imageCanvas.width, point.x));
  currentY = Math.max(0, Math.min(imageCanvas.height, point.y));
  const roi = getROI();

  if (roi.width >= 10 && roi.height >= 10) {
    hasROI = true;
    lastROI = roi;
    analyzeButton.disabled = false;
    setStatus(`<strong>ROI 已选择：</strong>坐标 (${roi.x}, ${roi.y})，尺寸 ${roi.width} × ${roi.height} px。<br />点击"开始分析"运行。`);
  } else {
    hasROI = false;
    lastROI = null;
    analyzeButton.disabled = true;
    setStatus(`<strong>当前状态：</strong>ROI 太小，请重新框选更大的区域。`);
  }
  drawROI();
});

clearRoiButton.addEventListener("click", clearROI);

analyzeButton.addEventListener("click", async () => {
  if (!currentAlgorithm || !currentImageFile || !hasROI) return;

  try {
    setStatus(`<strong>正在分析：</strong>${algorithmInfo[currentAlgorithm].name}……`);

    const formData = new FormData();
    formData.append("file", currentImageFile);
    formData.append("roi", JSON.stringify(getROI()));
    
    // 色卡模式附加参数
    if (currentAlgorithm === "colorChecker") {
      const colorSpace = colorSpaceSelect ? colorSpaceSelect.value : "sRGB";
      const whitePoint = whitePointSelect ? whitePointSelect.value : "D65";
      formData.append("color_space", colorSpace);
      formData.append("white_point", whitePoint);
    }

    const response = await fetch(`${API_BASE}/analyze/${currentAlgorithm}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    renderResult(result);
    setStatus(`<strong>分析完成：</strong>${algorithmInfo[currentAlgorithm].name}。`);
  } catch (error) {
    console.error(error);
    setStatus(`<strong>分析失败：</strong>${error.message}`);
    resultContainer.innerHTML = `
      <div class="result-card">
        <h4>错误信息</h4>
        <p>${error.message}</p>
      </div>
    `;
  }
});

function renderResult(result) {
  if (currentAlgorithm === "colorChecker" && result.status === "success") {
    renderColorCheckerResult(result);
  } else {
    resultContainer.innerHTML = `
      <div class="result-card">
        <h4>分析结果</h4>
        <pre>${JSON.stringify(result, null, 2)}</pre>
      </div>
    `;
  }
}

/**
 * 渲染 24 色卡分析结果
 */
function renderColorCheckerResult(result) {
  const stats = result.statistics;
  const patches = result.patches;
  const params = result.params;

  // 统计卡片
  let statsHtml = "";
  if (stats) {
    statsHtml = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="value">${stats.avg_delta_e !== null ? stats.avg_delta_e.toFixed(2) : "--"}</div>
          <div class="label">平均 ΔE</div>
        </div>
        <div class="stat-card">
          <div class="value">${stats.max_delta_e !== null ? stats.max_delta_e.toFixed(2) : "--"}</div>
          <div class="label">最大 ΔE</div>
        </div>
        <div class="stat-card">
          <div class="value">${stats.min_delta_e !== null ? stats.min_delta_e.toFixed(2) : "--"}</div>
          <div class="label">最小 ΔE</div>
        </div>
      </div>
    `;
  }

  // 色块数据表格
  let tableRows = "";
  if (patches && patches.length > 0) {
    tableRows = patches.map((p) => {
      const rgb = p.rgb.measured;
      const deltaEClass = p.delta_e > 5 ? "delta-e-high" : p.delta_e > 2 ? "delta-e-mid" : "delta-e-low";
      return `
        <tr>
          <td class="patch-index">${p.index}</td>
          <td><span class="color-swatch" style="background:rgb(${Math.round(rgb[0])},${Math.round(rgb[1])},${Math.round(rgb[2])})"></span>${p.name}</td>
          <td title="sRGB 编码值 (0-255)">(${rgb.map(v => v.toFixed(1)).join(", ")})</td>
          <td>${p.xyz.measured.map(v => v.toFixed(2)).join(", ")}</td>
          <td>${p.lab.measured.map(v => v.toFixed(2)).join(", ")}</td>
          <td>${p.luv.measured.map(v => v.toFixed(2)).join(", ")}</td>
          <td class="${deltaEClass}">${p.delta_e.toFixed(2)}</td>
        </tr>
      `;
    }).join("");
  }

  let tableHtml = "";
  const wpLabel = (whitePointSelect && whitePointSelect.value) ? whitePointSelect.value : "D65";
  if (tableRows) {
    tableHtml = `
      <table class="color-table">
        <thead>
          <tr>
            <th>#</th>
            <th>色块</th>
            <th title="sRGB 编码值 (0-255)，非线性">sRGB RGB</th>
            <th title="由 sRGB RGB 经 gamma 解码为线性 RGB 后换算">XYZ</th>
            <th>CIELAB ${wpLabel}</th>
            <th>CIELUV ${wpLabel}</th>
            <th>ΔE</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows}
        </tbody>
      </table>
    `;
  }

  resultContainer.innerHTML = `
    <div class="result-card">
      <h4>24 色卡分析结果</h4>
      <p><strong>色彩空间：</strong>${params?.color_space || "sRGB"} &nbsp;|&nbsp; <strong>白点：</strong>${params?.white_point || "D65"}</p>
      <p class="rgb-hint">RGB 列显示的是 <strong>sRGB 编码值 (0–255)</strong>；线性 RGB 仅用于内部换算 XYZ，不在界面展示。参考值固定取自 sRGB 标准色卡。</p>
      ${statsHtml}
      ${tableHtml}
    </div>
  `;

  // 分析完成后，在图上保留 24 色块网格叠加
  if (lastROI) {
    redrawImage();
    drawColorCheckerGrid(lastROI);
  }
}

// 查看参考值按钮（再次点击收起）
if (loadRefButton) {
  loadRefButton.addEventListener("click", async () => {
    const refContainer = document.getElementById("refTableContainer");
    // 已显示则收起
    if (refContainer && refContainer.innerHTML.trim() !== "") {
      refContainer.innerHTML = "";
      return;
    }
    console.log("点击了查看参考值按钮");
    try {
      const response = await fetch(`${API_BASE}/reference/colorchecker`);
      console.log("参考值API响应:", response.status);
      const data = await response.json();
      console.log("参考值数据:", data);
      if (data.status === "success") {
        renderReferenceTable(data.patches);
      } else {
        alert("加载参考值失败: " + (data.detail || "未知错误"));
      }
    } catch (error) {
      console.error("加载参考值失败:", error);
      alert("加载参考值失败: " + error.message);
    }
  });
}

// 上传自定义参考值
if (uploadRefButton && refFileInput) {
  uploadRefButton.addEventListener("click", () => {
    refFileInput.click();
  });
  
  refFileInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const jsonData = JSON.parse(e.target.result);
        if (jsonData.patches && Array.isArray(jsonData.patches)) {
          // 存储到本地，分析时传递给后端
          localStorage.setItem("colorchecker_custom_ref", JSON.stringify(jsonData));
          alert(`已加载自定义参考值: ${jsonData.name || "未命名"}\n共 ${jsonData.patches.length} 个色块`);
        } else {
          alert("文件格式错误: 缺少 patches 数组");
        }
      } catch (err) {
        alert("文件解析失败: " + err.message);
      }
    };
    reader.readAsText(file);
  });
}

function renderReferenceTable(patches) {
  const wp = (whitePointSelect && whitePointSelect.value) ? whitePointSelect.value : "D65";
  let tableHtml = `
    <div style="margin-top:20px;overflow:auto;">
      <h4 style="margin:0 0 12px 0;">当前参考值 (${patches.length} 色块)</h4>
      <table class="color-table">
        <thead>
          <tr><th>#</th><th>名称</th><th title="sRGB 编码值 (0-255)">sRGB</th><th>LAB ${wp}</th></tr>
        </thead>
        <tbody>
  `;
  
  patches.forEach((p, i) => {
    const rgb = p.rgb || p.RGB || [0, 0, 0];
    const lab = p.lab || p.LAB || [0, 0, 0];
    tableHtml += `
      <tr>
        <td>${i + 1}</td>
        <td><span class="color-swatch" style="background:rgb(${rgb[0]},${rgb[1]},${rgb[2]})"></span>${p.name}</td>
        <td>${rgb.join(", ")}</td>
        <td>${lab.map(v => typeof v === "number" ? v.toFixed(2) : v).join(", ")}</td>
      </tr>
    `;
  });
  
  tableHtml += `</tbody></table></div>`;
  
  // 显示在色卡参数面板下方的 refTableContainer 中
  const refContainer = document.getElementById("refTableContainer");
  if (refContainer) {
    refContainer.innerHTML = tableHtml;
  } else {
    // fallback: 显示在结果区域
    resultContainer.innerHTML = tableHtml;
  }
}

backButton.addEventListener("click", () => {
  workspace.classList.add("hidden");
  document.querySelector(".algorithm-section").scrollIntoView({ behavior: "smooth", block: "start" });
});
