const ALL_COINS=["BTC","ETH","BNB","SOL","XRP","ADA","DOGE","TON","AVAX","DOT"];
const KEY="coins-selected";

function load(){
  try{ return JSON.parse(localStorage.getItem(KEY)) || []; }catch{ return []; }
}
function save(list){
  try{ localStorage.setItem(KEY, JSON.stringify(list)); }catch{}
}

const selected=new Set(load());
const listEl=document.getElementById("coin-list");
const searchEl=document.getElementById("coin-search");
const countEl=document.getElementById("selected-count");
const resultEl=document.getElementById("search-result-count");
const clearBtn=document.getElementById("clear-selected");

function updateCount(){ countEl.textContent = selected.size>0 ? `${selected.size} انتخاب شده` : "—"; }

function render(filter=""){ 
  listEl.innerHTML="";
  const f=(filter||"").trim().toUpperCase();
  const filtered=ALL_COINS.filter(c=>!f||c.includes(f));
  if(resultEl) resultEl.textContent=`${filtered.length} از ${ALL_COINS.length}`;
  for(const sym of filtered){
    const li=document.createElement("li");
    li.innerHTML=`<label class=\"item\"><input type=\"checkbox\" value=\"${sym}\"><span>${sym}/USDT</span></label>`;
    const cb=li.querySelector("input");
    cb.checked=selected.has(sym);
    cb.addEventListener("change",()=>{
      if(cb.checked) selected.add(sym); else selected.delete(sym);
      save([...selected]);
      updateCount();
    });
    listEl.appendChild(li);
  }
  updateCount();
}

searchEl?.addEventListener("input", e=>render(e.target.value));
clearBtn?.addEventListener("click", ()=>{ selected.clear(); save([]); render(searchEl?.value||"");});
window.addEventListener("beforeunload", ()=>save([...selected]));

render();

