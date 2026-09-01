from flask import Flask, render_template_string, request, jsonify, session, Response
import json
import os
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())
# ========== 配置 ==========
# 密码优先读环境变量，部署后在Render后台设置，更安全
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")
DATA_FILE = "pet_data.json"
# 允许的加成类型（下拉固定选项）
ALLOWED_BONUS = ["物攻", "魔攻", "生命", "速度"]
# 重量上限
MAX_WEIGHT = 100
# 加成属性词白名单（自然语言解析时用于识别加成字段）
ATTR_WORDS = ["物攻", "魔攻", "速度", "防御", "精力", "HP", "hp",
               "命中", "闪避", "暴击", "抗暴", "物防", "特防", "魔抗"]
# ==========================

def migrate_eggs(d):
    """将旧格式 big_eggs（字符串列表）迁移为结构化对象列表，并补全字段。
    返回 (迁移后的数据, 是否发生了变更)。"""
    if "big_eggs" not in d:
        d["big_eggs"] = []
        return d, True
    new_eggs = []
    changed = False
    for item in d["big_eggs"]:
        if isinstance(item, str):
            # 旧格式：纯字符串 -> 转为对象，数量默认1
            new_eggs.append({"info": item, "bonus": "", "weight": "", "count": 1})
            changed = True
        else:
            # 新格式：补全可能缺失的字段
            egg = {
                "info": item.get("info", ""),
                "bonus": item.get("bonus", ""),
                "weight": item.get("weight", ""),
                "count": item.get("count", 1),
            }
            new_eggs.append(egg)
            if egg != item:
                changed = True
    if changed:
        d["big_eggs"] = new_eggs
    return d, changed

def init_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"pets": [], "big_eggs": [], "settings": {"background": "", "brightness": 100}}, f, ensure_ascii=False, indent=2)

def migrate_settings(d):
    """补全 settings 字段，返回 (迁移后数据, 是否变更)"""
    changed = False
    if "settings" not in d or not isinstance(d.get("settings"), dict):
        d["settings"] = {"background": "", "brightness": 100}
        changed = True
    else:
        s = d["settings"]
        if "background" not in s:
            s["background"] = ""
            changed = True
        if "brightness" not in s:
            s["brightness"] = 100
            changed = True
        # 亮度范围校验
        try:
            b = int(s["brightness"])
            if b < 10 or b > 100:
                s["brightness"] = 100
                changed = True
        except (ValueError, TypeError):
            s["brightness"] = 100
            changed = True
    return d, changed

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
    d, changed1 = migrate_eggs(d)
    d, changed2 = migrate_settings(d)
    if changed1 or changed2:
        save_data(d)
    return d

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def find_egg_index(d, info, bonus, weight):
    """在 big_eggs 中查找 info+bonus+weight 三者完全相同的记录，返回下标，找不到返回 -1。"""
    for i, egg in enumerate(d["big_eggs"]):
        if (egg.get("info", "") == info
                and egg.get("bonus", "") == bonus
                and egg.get("weight", "") == weight):
            return i
    return -1

init_data()

HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>洛克王国世界 精灵台账</title>
<style>
*{box-sizing:border-box;font-family:"Microsoft Yahei",sans-serif;margin:0;padding:0;}
body{max-width:1100px;margin:0 auto;padding:20px;background:#f0f2f5;min-height:100vh;}
#bgLayer{position:fixed;inset:0;z-index:-2;background-size:cover;background-position:center;background-attachment:fixed;}
body::before{content:"";position:fixed;inset:0;background:rgba(255,255,255,.78);z-index:-1;}
.pet-img{width:64px;height:64px;object-fit:contain;border-radius:10px;background:#f7f8fb;border:1px solid #eee;}
.pet-card{display:flex;align-items:center;gap:14px;}
.section-title{display:flex;justify-content:space-between;align-items:center;cursor:pointer;user-select:none;}
.section-title .arrow{transition:.2s;font-size:16px;}
.collapsed .arrow{transform:rotate(-90deg);}
.collapse-body{overflow:hidden;transition:max-height .25s ease;}
.settings{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px;}
.settings label{font-size:13px;color:#555;}
.bg-preview{width:46px;height:30px;object-fit:cover;border-radius:5px;border:1px solid #ddd;}
h1{text-align:center;color:#1a1a2e;margin-bottom:20px;}
.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);}
.card h2{color:#16213e;margin-bottom:16px;font-size:20px;border-left:4px solid #0f3460;padding-left:10px;}
.auth-bar{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:16px 20px;border-radius:12px;margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.auth-bar input{padding:8px 14px;border:none;border-radius:6px;font-size:14px;flex:1;min-width:150px;color:#333;}
.auth-bar button{padding:8px 18px;background:#fff;color:#667eea;border:none;border-radius:6px;cursor:pointer;font-weight:bold;font-size:14px;}
.auth-bar .status{font-size:14px;}
.auth-bar .logout{background:transparent;color:#fff;border:1px solid #fff;}
.auth-bar .export-btn{background:rgba(255,255,255,.2);color:#fff;border:1px solid rgba(255,255,255,.5);}
table{width:100%;border-collapse:collapse;margin-top:12px;}
th,td{padding:12px 10px;text-align:left;border-bottom:1px solid #eee;}
th{background:#f8f9fc;color:#333;font-weight:600;}
tr:hover{background:#f8f9fc;}
input,select{padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px;}
.add-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;}
.add-row input,.add-row select{flex:1;min-width:100px;}
.btn{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:14px;}
.btn-primary{background:#0f3460;color:#fff;}
.btn-danger{background:#e94560;color:#fff;}
.hidden{display:none !important;}
.readonly-tip{background:#fff3cd;color:#856404;padding:10px 16px;border-radius:6px;margin-bottom:16px;font-size:14px;}
.import-area{margin-top:12px;padding:12px;background:#f8f9fc;border-radius:8px;}
.filter-bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px;padding:10px 14px;background:#f8f9fc;border-radius:8px;}
.filter-bar label{font-size:13px;color:#555;}
.filter-bar select{min-width:120px;}
.count-badge{display:inline-block;min-width:28px;text-align:center;background:#0f3460;color:#fff;border-radius:12px;padding:2px 8px;font-size:13px;font-weight:bold;}
</style>
</head>
<body>
<div id="bgLayer"></div>
<h1>洛克王国世界 精灵台账</h1>
<div class="auth-bar">
    <span class="status" id="authStatus">🔒 只读模式</span>
    <input type="password" id="pwdInput" placeholder="管理员密码">
    <button onclick="login()">解锁编辑</button>
    <button class="logout hidden" id="logoutBtn" onclick="logout()">退出</button>
    <button class="export-btn hidden" id="exportBtn" onclick="exportData()">导出备份</button>
</div>
<div class="readonly-tip hidden" id="readonlyTip">当前为只读模式，只能查看。如需编辑请输入管理员密码解锁。</div>
<div class="card" id="petCard">
    <div class="section-title" onclick="toggleSection('petCard')">
        <h2>我的精灵列表</h2><span class="arrow">▼</span>
    </div>
    <div class="collapse-body">
    <div class="add-row hidden" id="petAddBar">
        <input id="petName" placeholder="精灵名字">
        <select id="petSex">
            <option value="雄性">雄性</option>
            <option value="雌性">雌性</option>
            <option value="无性别">无性别</option>
        </select>
        <input id="petEggGroup" placeholder="蛋组">
        <input id="petBonus" placeholder="加成">
        <label style="display:flex;align-items:center;gap:5px;">图片 <input type="file" id="petImage" accept="image/*"></label>
        <button class="btn btn-primary" onclick="addPet()">新增</button>
    </div>
    <table>
        <thead><tr><th>图片</th><th>名字</th><th>性别</th><th>蛋组</th><th>加成</th><th id="petOpHead" class="hidden">操作</th></tr></thead>
        <tbody id="petTableBody"></tbody>
    </table>
    </div>
</div>
<div class="card" id="eggCard">
    <div class="section-title" onclick="toggleSection('eggCard')">
        <h2>大块头蛋</h2><span class="arrow">▼</span>
    </div>
    <div class="collapse-body">
    <div class="filter-bar">
        <label>精灵筛选：</label>
        <select id="filterInfo" onchange="loadEggs()">
            <option value="">全部</option>
        </select>
        <label>加成筛选：</label>
        <select id="filterBonus" onchange="loadEggs()">
            <option value="">全部</option>
        </select>
        <label>蛋重筛选：</label>
        <select id="filterWeight" onchange="loadEggs()">
            <option value="">全部</option>
        </select>
        <button class="btn" onclick="resetEggFilter()">重置筛选</button>
        <span id="eggCountTip" style="font-size:13px;color:#888;margin-left:auto;"></span>
    </div>
    <div class="add-row hidden" id="eggParseBar">
        <input id="eggParseText" placeholder="快速录入：输入一段描述自动解析，如&quot;火神蛋 物攻 85&quot;" style="flex:2;min-width:240px;">
        <button class="btn btn-primary" onclick="parseEgg()">解析录入</button>
    </div>
    <div class="add-row hidden" id="eggAddBar">
        <input id="eggInfo" placeholder="蛋信息（如：火神蛋）">
        <select id="eggBonus">
            <option value="">加成（可选）</option>
            <option value="物攻">物攻</option>
            <option value="魔攻">魔攻</option>
            <option value="生命">生命</option>
            <option value="速度">速度</option>
        </select>
        <input id="eggWeight" placeholder="重量(0-100)" type="number" min="0" max="100" step="0.1">
        <button class="btn btn-primary" onclick="addEgg()">新增</button>
    </div>
    <table>
        <thead><tr><th>蛋信息</th><th>加成</th><th>蛋重</th><th>数量</th><th id="eggOpHead" class="hidden">操作</th></tr></thead>
        <tbody id="eggTableBody"></tbody>
    </table>
    <div class="import-area hidden" id="importArea">
        <p style="margin-bottom:8px;font-size:13px;color:#666;">数据恢复（选择之前导出的JSON文件）：</p>
        <input type="file" id="importFile" accept=".json">
        <button class="btn btn-primary" onclick="importData()">恢复数据</button>
    </div>
    </div>
</div>
<div class="card hidden" id="settingsCard">
    <h2>网页外观设置</h2>
    <div class="settings">
        <label>背景图片：</label>
        <input type="file" id="bgFile" accept="image/*" onchange="changeBackground(this)">
        <button class="btn" onclick="clearBackground()">恢复默认背景</button>
        <span id="bgStatus" style="font-size:13px;color:#666;"></span>
    </div>
    <div class="settings">
        <label>外观亮度：</label>
        <input type="range" id="brightnessRange" min="10" max="100" value="100" oninput="onBrightnessInput(this.value)" onchange="saveBrightness(this.value)" style="flex:1;max-width:300px;">
        <span id="brightnessValue" style="font-size:13px;color:#555;min-width:40px;">100%</span>
    </div>
</div>
<script>
let isAdmin = false;
async function api(url, method="GET", body=null){
    let opt = {method, headers:{"Content-Type":"application/json"}};
    if(body) opt.body = JSON.stringify(body);
    let res = await fetch(url, opt);
    return res.json();
}
async function login(){
    let pwd = document.getElementById("pwdInput").value;
    let r = await api("/api/login","POST",{password:pwd});
    if(r.ok){
        isAdmin = true;
        document.getElementById("authStatus").textContent = "✅ 已解锁编辑";
        document.getElementById("readonlyTip").classList.add("hidden");
        ["logoutBtn","exportBtn","petAddBar","eggAddBar","eggParseBar","petOpHead","eggOpHead","importArea","settingsCard"].forEach(id=>document.getElementById(id).classList.remove("hidden"));
        document.getElementById("pwdInput").classList.add("hidden");
        loadPets(); loadEggs();
    } else alert("密码错误");
}
async function logout(){ await api("/api/logout","POST"); location.reload(); }
async function checkAuth(){
    let r = await api("/api/check");
    if(r.authed){
        isAdmin = true;
        document.getElementById("authStatus").textContent = "✅ 已解锁编辑";
        ["logoutBtn","exportBtn","petAddBar","eggAddBar","eggParseBar","petOpHead","eggOpHead","importArea","settingsCard"].forEach(id=>document.getElementById(id).classList.remove("hidden"));
        document.getElementById("pwdInput").classList.add("hidden");
    } else document.getElementById("readonlyTip").classList.remove("hidden");
}
async function loadPets(){
    let arr = await api("/api/pets");
    let tb = document.getElementById("petTableBody"); tb.innerHTML = "";
    arr.forEach((item,idx)=>{
        let tr = document.createElement("tr");
        let op = isAdmin ? `<td><button class="btn btn-danger" onclick="delPet(${idx})">删除</button></td>` : "";
        let img = item.image ? `<img class="pet-img" src="${item.image}" alt="${item.name}">` : `<div class="pet-img" style="display:flex;align-items:center;justify-content:center;color:#aaa;">暂无</div>`;
        tr.innerHTML = `<td>${img}</td><td>${item.name}</td><td>${item.sex}</td><td>${item.egg_group}</td><td>${item.bonus}</td>${op}`;
        tb.appendChild(tr);
    });
}
async function addPet(){
    if(!isAdmin) return;
    let name=document.getElementById("petName").value.trim(), sex=document.getElementById("petSex").value;
    let eg=document.getElementById("petEggGroup").value.trim(), bonus=document.getElementById("petBonus").value.trim();
    let imageFile=document.getElementById("petImage").files[0];
    if(!name){alert("名字不能为空");return;}
    let image="";
    if(imageFile){
        if(imageFile.size>2*1024*1024){alert("图片建议控制在2MB以内");return;}
        image=await new Promise(resolve=>{
            const r=new FileReader(); r.onload=e=>resolve(e.target.result); r.readAsDataURL(imageFile);
        });
    }
    let r = await api("/api/pets/add","POST",{name,sex,egg_group:eg,bonus,image});
    if(r.ok){ ["petName","petEggGroup","petBonus"].forEach(id=>document.getElementById(id).value=""); document.getElementById("petImage").value=""; loadPets(); }
}
async function delPet(idx){
    if(!isAdmin||!confirm("确定删除？")) return;
    let r = await api("/api/pets/del","POST",{index:idx});
    if(r.ok) loadPets();
}

/* ========== 大块头蛋：筛选 + 结构化 + 解析录入 ========== */

function updateEggFilterOptions(arr){
    /* 从数据中提取不重复的精灵、加成和蛋重，更新筛选下拉框，保留当前选中值 */
    let infoSelect = document.getElementById("filterInfo");
    let bonusSelect = document.getElementById("filterBonus");
    let weightSelect = document.getElementById("filterWeight");
    let curI = infoSelect.value;
    let curB = bonusSelect.value;
    let curW = weightSelect.value;

    let infos = [...new Set(arr.map(i=>i.info).filter(v=>v))];
    let bonuses = [...new Set(arr.map(i=>i.bonus).filter(b=>b))];
    let weights = [...new Set(arr.map(i=>i.weight).filter(w=>w))];

    infoSelect.innerHTML = '<option value="">全部</option>' + infos.map(v=>`<option value="${v}">${v}</option>`).join('');
    bonusSelect.innerHTML = '<option value="">全部</option>' + bonuses.map(b=>`<option value="${b}">${b}</option>`).join('');
    weightSelect.innerHTML = '<option value="">全部</option>' + weights.map(w=>`<option value="${w}">${w}</option>`).join('');

    infoSelect.value = curI;
    bonusSelect.value = curB;
    weightSelect.value = curW;
}

function resetEggFilter(){
    document.getElementById("filterInfo").value = "";
    document.getElementById("filterBonus").value = "";
    document.getElementById("filterWeight").value = "";
    loadEggs();
}

async function loadEggs(){
    let arr = await api("/api/big_eggs");
    let filterI = document.getElementById("filterInfo").value;
    let filterB = document.getElementById("filterBonus").value;
    let filterW = document.getElementById("filterWeight").value;

    /* 更新筛选下拉选项（基于全量数据） */
    updateEggFilterOptions(arr);

    /* 应用筛选 */
    let filtered = arr.filter(item => {
        if(filterI && item.info !== filterI) return false;
        if(filterB && item.bonus !== filterB) return false;
        if(filterW && item.weight !== filterW) return false;
        return true;
    });

    /* 统计提示 */
    let totalCount = filtered.reduce((s, i)=>s + (i.count||1), 0);
    document.getElementById("eggCountTip").textContent =
        `共 ${filtered.length} 种 / ${totalCount} 个`;

    let tb = document.getElementById("eggTableBody"); tb.innerHTML = "";
    arr.forEach((item, origIdx)=>{
        /* 筛选后仍用原始下标做删除，保证后端定位准确 */
        if(filterI && item.info !== filterI) return;
        if(filterB && item.bonus !== filterB) return;
        if(filterW && item.weight !== filterW) return;
        let tr = document.createElement("tr");
        let op = isAdmin ? `<td><button class="btn btn-danger" onclick="delEgg(${origIdx})">删除</button></td>` : "";
        let cnt = item.count||1;
        let countCell = isAdmin
            ? `<td style="white-space:nowrap;"><button class="btn" onclick="changeEggCount(${origIdx},-1,${cnt})" style="padding:4px 10px;min-width:30px;">−</button> <span class="count-badge">${cnt}</span> <button class="btn" onclick="changeEggCount(${origIdx},1)" style="padding:4px 10px;min-width:30px;">+</button></td>`
            : `<td><span class="count-badge">${cnt}</span></td>`;
        tr.innerHTML = `<td>${item.info}</td><td>${item.bonus||'<span style="color:#aaa;">-</span>'}</td><td>${item.weight||'<span style="color:#aaa;">-</span>'}</td>${countCell}${op}`;
        tb.appendChild(tr);
    });
}

async function addEgg(){
    if(!isAdmin) return;
    let info = document.getElementById("eggInfo").value.trim();
    let bonus = document.getElementById("eggBonus").value;
    let weight = document.getElementById("eggWeight").value.trim();
    if(!info){alert("蛋信息不能为空");return;}
    if(weight !== ""){
        let w = Number(weight);
        if(isNaN(w) || w < 0 || w > 100){alert("重量必须是 0-100 之间的数字");return;}
    }
    let r = await api("/api/egg/add","POST",{info,bonus,weight});
    if(r.ok){
        document.getElementById("eggInfo").value="";
        document.getElementById("eggBonus").value="";
        document.getElementById("eggWeight").value="";
        loadEggs();
    } else {
        alert("新增失败：" + (r.msg||""));
    }
}

async function parseEgg(){
    if(!isAdmin) return;
    let text = document.getElementById("eggParseText").value.trim();
    if(!text){alert("请输入描述文本");return;}
    let r = await api("/api/egg/parse","POST",{text});
    if(r.ok){
        let p = r.parsed;
        alert(`解析成功并录入：\n蛋信息：${p.info}\n加成：${p.bonus||"（未识别）"}\n蛋重：${p.weight||"（未识别）"}`);
        document.getElementById("eggParseText").value="";
        loadEggs();
    } else {
        alert("解析失败：" + (r.msg||""));
    }
}

async function changeEggCount(idx, delta, curCount){
    if(!isAdmin) return;
    /* 减到 0 时确认是否删除 */
    if(delta === -1 && curCount !== undefined && curCount <= 1){
        if(!confirm("数量已为 1，再减将删除该记录，确定？")) return;
    }
    let r = await api("/api/egg/count","POST",{index:idx,delta});
    if(r.ok) loadEggs();
    else alert("操作失败：" + (r.msg||""));
}

async function delEgg(idx){
    if(!isAdmin||!confirm("确定删除该蛋记录？")) return;
    let r = await api("/api/egg/del","POST",{index:idx});
    if(r.ok) loadEggs();
}

/* ========== 以下为原有通用功能 ========== */

function toggleSection(id){
    const card=document.getElementById(id);
    card.classList.toggle("collapsed");
    const body=card.querySelector(".collapse-body");
    body.style.maxHeight=card.classList.contains("collapsed") ? "0px" : body.scrollHeight+"px";
    localStorage.setItem("collapse_"+id, card.classList.contains("collapsed") ? "1" : "0");
}
function restoreCollapse(){
    ["petCard","eggCard"].forEach(id=>{
        const card=document.getElementById(id), body=card.querySelector(".collapse-body");
        if(localStorage.getItem("collapse_"+id)==="1"){
            card.classList.add("collapsed"); body.style.maxHeight="0px";
        }else body.style.maxHeight=body.scrollHeight+"px";
    });
}
/* ========== 外观设置（全局共享，存在后端） ========== */
function applyBackground(url){
    let layer = document.getElementById("bgLayer");
    if(url){
        layer.style.backgroundImage = 'url("' + url + '")';
        document.getElementById("bgStatus").textContent = "已使用自定义背景";
    } else {
        layer.style.backgroundImage = "";
        document.getElementById("bgStatus").textContent = "已恢复默认背景";
    }
}
function applyBrightness(val){
    let layer = document.getElementById("bgLayer");
    layer.style.filter = "brightness(" + val + "%)";
    document.getElementById("brightnessValue").textContent = val + "%";
    document.getElementById("brightnessRange").value = val;
}
async function loadSettings(){
    /* 页面加载时从后端获取全局外观设置并应用（所有人可见） */
    try{
        let s = await api("/api/settings");
        applyBackground(s.background || "");
        applyBrightness(s.brightness || 100);
    }catch(e){ console.warn("加载外观设置失败", e); }
}
function changeBackground(input){
    if(!isAdmin) return;
    const file=input.files[0];
    if(!file)return;
    if(file.size > 3*1024*1024){alert("图片建议控制在 3MB 以内");return;}
    const reader=new FileReader();
    reader.onload=async e=>{
        let base64 = e.target.result;
        let r = await api("/api/settings/update","POST",{background:base64});
        if(r.ok){
            applyBackground(base64);
        } else alert("保存失败：" + (r.msg||""));
    };
    reader.readAsDataURL(file);
}
async function clearBackground(){
    if(!isAdmin) return;
    if(!confirm("确定恢复默认背景？")) return;
    let r = await api("/api/settings/update","POST",{background:""});
    if(r.ok){
        applyBackground("");
        document.getElementById("bgFile").value = "";
    }
}
function onBrightnessInput(val){
    /* 拖动滑块时实时预览，不保存 */
    applyBrightness(val);
}
async function saveBrightness(val){
    /* 松开滑块时保存到后端 */
    if(!isAdmin) return;
    let r = await api("/api/settings/update","POST",{brightness:parseInt(val)});
    if(!r.ok) alert("亮度保存失败：" + (r.msg||""));
}
function exportData(){
    window.open("/api/export","_blank");
}
async function importData(){
    let file = document.getElementById("importFile").files[0];
    if(!file){alert("请选择文件");return;}
    let text = await file.text();
    let r = await api("/api/import","POST",JSON.parse(text));
    if(r.ok){alert("恢复成功");loadPets();loadEggs();}
    else alert("恢复失败："+r.msg);
}
window.onload = ()=>{ checkAuth(); loadPets(); loadEggs(); loadSettings(); setTimeout(restoreCollapse,100); };
</script>
</body>
</html>
'''

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/login", methods=["POST"])
def login():
    j = request.get_json()
    if j.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("admin", None)
    return jsonify({"ok": True})

@app.route("/api/check")
def check():
    return jsonify({"authed": session.get("admin", False)})

@app.route("/api/pets")
def api_pets():
    return jsonify(load_data()["pets"])

@app.route("/api/big_eggs")
def api_eggs():
    return jsonify(load_data()["big_eggs"])

@app.route("/api/export")
def export_data():
    d = load_data()
    return Response(
        json.dumps(d, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=pet_backup.json"}
    )

@app.route("/api/import", methods=["POST"])
def import_data():
    if not session.get("admin"):
        return jsonify({"ok": False, "msg": "无权限"}), 403
    try:
        j = request.get_json()
        if "pets" in j and "big_eggs" in j:
            # 导入时也做一次格式迁移，兼容旧备份
            j, _ = migrate_eggs(j)
            save_data(j)
            return jsonify({"ok": True})
        return jsonify({"ok": False, "msg": "文件格式不对"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

# ========== 外观设置（全局共享） ==========
@app.route("/api/settings")
def api_settings():
    """公开接口：所有人都能读取当前外观设置"""
    d = load_data()
    return jsonify(d.get("settings", {"background": "", "brightness": 100}))

@app.route("/api/settings/update", methods=["POST"])
def api_settings_update():
    """管理员接口：更新背景图和/或亮度，传入什么更新什么"""
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json() or {}
    d = load_data()
    s = d["settings"]
    if "background" in j:
        s["background"] = j["background"]
    if "brightness" in j:
        try:
            b = int(j["brightness"])
            if 10 <= b <= 100:
                s["brightness"] = b
            else:
                return jsonify({"ok": False, "msg": "亮度必须在 10-100 之间"}), 400
        except (ValueError, TypeError):
            return jsonify({"ok": False, "msg": "亮度必须是整数"}), 400
    save_data(d)
    return jsonify({"ok": True, "settings": s})

def require_admin():
    return session.get("admin", False)

@app.route("/api/pets/add", methods=["POST"])
def pet_add():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    d = load_data()
    d["pets"].append({"name": j["name"], "sex": j["sex"], "egg_group": j["egg_group"], "bonus": j["bonus"], "image": j.get("image","")})
    save_data(d)
    return jsonify({"ok": True})

@app.route("/api/pets/del", methods=["POST"])
def pet_del():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    d = load_data()
    idx = j["index"]
    if 0 <= idx < len(d["pets"]):
        del d["pets"][idx]
        save_data(d)
    return jsonify({"ok": True})

# ========== 大块头蛋：结构化新增（自动合并） ==========
@app.route("/api/egg/add", methods=["POST"])
def egg_add():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    info = j.get("info", "").strip()
    bonus = j.get("bonus", "").strip()
    weight_raw = j.get("weight", "")
    # 重量校验：必须是 0-MAX_WEIGHT 的数字，允许为空；统一存为字符串
    weight = ""
    if weight_raw != "" and weight_raw is not None:
        try:
            w = float(weight_raw)
        except (ValueError, TypeError):
            return jsonify({"ok": False, "msg": "重量必须是数字"}), 400
        if w < 0 or w > MAX_WEIGHT:
            return jsonify({"ok": False, "msg": "重量必须在 0-%d 之间" % MAX_WEIGHT}), 400
        weight = str(int(w)) if w == int(w) else str(w)
    # 加成校验：必须在允许列表中或为空
    if bonus and bonus not in ALLOWED_BONUS:
        return jsonify({"ok": False, "msg": "加成类型不合法"}), 400
    if not info:
        return jsonify({"ok": False, "msg": "蛋信息不能为空"}), 400
    d = load_data()
    idx = find_egg_index(d, info, bonus, weight)
    if idx >= 0:
        # 三者相同 -> 合并，数量+1
        d["big_eggs"][idx]["count"] = d["big_eggs"][idx].get("count", 1) + 1
    else:
        d["big_eggs"].append({"info": info, "bonus": bonus, "weight": weight, "count": 1})
    save_data(d)
    return jsonify({"ok": True})

# ========== 大块头蛋：数量手动加减 ==========
@app.route("/api/egg/count", methods=["POST"])
def egg_count():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    idx = j.get("index")
    delta = j.get("delta", 0)
    d = load_data()
    if idx is None or not (0 <= idx < len(d["big_eggs"])):
        return jsonify({"ok": False, "msg": "记录不存在"}), 400
    if delta not in (-1, 1):
        return jsonify({"ok": False, "msg": "delta 必须是 1 或 -1"}), 400
    egg = d["big_eggs"][idx]
    new_count = egg.get("count", 1) + delta
    if new_count <= 0:
        del d["big_eggs"][idx]
    else:
        egg["count"] = new_count
    save_data(d)
    return jsonify({"ok": True})

# ========== 大块头蛋：自然语言解析录入 ==========
@app.route("/api/egg/parse", methods=["POST"])
def egg_parse():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    text = j.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "msg": "文本不能为空"}), 400

    work = text

    # ---- 1. 解析加成：从固定选项中匹配关键词 ----
    bonus = ""
    for kw in ALLOWED_BONUS:
        if kw in work:
            bonus = kw
            work = work.replace(kw, "", 1)
            break

    # ---- 2. 解析重量：纯数字 0-MAX_WEIGHT，可带"蛋重/重量/重"前缀 ----
    weight = ""
    wm = re.search(r'(?:蛋重|重量|重)\s*[：:]?\s*(\d+(?:\.\d+)?)', work)
    if not wm:
        # 不带前缀：直接找数字（加成已是纯文字，不会冲突）
        wm = re.search(r'(\d+(?:\.\d+)?)', work)
    if wm:
        try:
            w = float(wm.group(1))
            if 0 <= w <= MAX_WEIGHT:
                weight = str(int(w)) if w == int(w) else str(w)
                work = work[:wm.start()] + work[wm.end():]
        except (ValueError, TypeError):
            pass

    # ---- 3. 剩余文本作为蛋信息，清理首尾标点和多余空格 ----
    info = work.strip()
    info = re.sub(r'^[，,。.、\s：:；;]+', '', info)
    info = re.sub(r'[，,。.、\s：:；;]+$', '', info)
    info = re.sub(r'\s+', '', info)

    if not info:
        return jsonify({"ok": False, "msg": "无法从文本中识别蛋信息，请检查输入格式"}), 400

    # ---- 4. 录入（自动合并） ----
    d = load_data()
    idx = find_egg_index(d, info, bonus, weight)
    if idx >= 0:
        d["big_eggs"][idx]["count"] = d["big_eggs"][idx].get("count", 1) + 1
    else:
        d["big_eggs"].append({"info": info, "bonus": bonus, "weight": weight, "count": 1})
    save_data(d)

    return jsonify({"ok": True, "parsed": {"info": info, "bonus": bonus, "weight": weight}})

@app.route("/api/egg/del", methods=["POST"])
def egg_del():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    d = load_data()
    idx = j["index"]
    if 0 <= idx < len(d["big_eggs"]):
        del d["big_eggs"][idx]
        save_data(d)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
