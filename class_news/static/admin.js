const keyInput=document.getElementById('adminKey');
const loginBox=document.getElementById('loginBox');
const panel=document.getElementById('adminPanel');
const loginMsg=document.getElementById('loginMsg');
const form=document.getElementById('newsForm');
const editingId=document.getElementById('editingId');
const title=document.getElementById('title');
const content=document.getElementById('content');
const image=document.getElementById('image');
const removeImage=document.getElementById('removeImage');
const formMsg=document.getElementById('formMsg');
const newsList=document.getElementById('adminNewsList');
let adminKey=sessionStorage.getItem('adminKey')||'';
function setMessage(el,msg,ok=false){el.textContent=msg;el.className='message'+(ok?' ok':'');}
async function login(){
  const key=keyInput.value.trim();
  const fd=new FormData(); fd.append('key',key);
  const r=await fetch('/api/admin/login',{method:'POST',body:fd});
  if(!r.ok){setMessage(loginMsg,'관리자 키가 올바르지 않습니다.');return;}
  adminKey=key; sessionStorage.setItem('adminKey',key); loginBox.classList.add('hidden'); panel.classList.remove('hidden'); loadNews();
}
document.getElementById('loginBtn').onclick=login;
keyInput.addEventListener('keydown',e=>{if(e.key==='Enter')login()});
document.getElementById('newBtn').onclick=resetForm;
document.getElementById('cancelBtn').onclick=resetForm;
function resetForm(){editingId.value='';title.value='';content.value='';image.value='';removeImage.checked=false;setMessage(formMsg,'');window.scrollTo({top:200,behavior:'smooth'});}
async function loadNews(){
 const r=await fetch('/api/news'); const data=await r.json();
 newsList.innerHTML=data.length?data.map(n=>`<div class="card admin-item"><strong>${esc(n.title)}</strong><div class="news-date">${n.created_at} · ❤️ ${n.likes}</div><div class="admin-actions"><button class="secondary" onclick="editNews(${n.id})">수정</button><button class="danger" onclick="deleteNews(${n.id})">삭제</button></div></div>`).join(''):'<div class="empty">등록된 뉴스가 없습니다.</div>';
}
async function editNews(id){
 const r=await fetch(`/api/news/${id}`); const n=await r.json(); editingId.value=n.id;title.value=n.title;content.value=n.content;removeImage.checked=false;window.scrollTo({top:200,behavior:'smooth'});
}
async function deleteNews(id){
 if(!confirm('정말 삭제할까요?'))return;
 const r=await fetch(`/api/news/${id}?key=${encodeURIComponent(adminKey)}`,{method:'DELETE'});
 if(r.ok)loadNews(); else alert('삭제 실패');
}
form.onsubmit=async e=>{
 e.preventDefault(); setMessage(formMsg,'저장 중...');
 const fd=new FormData(); fd.append('key',adminKey); fd.append('title',title.value); fd.append('content',content.value); if(image.files[0])fd.append('image',image.files[0]); fd.append('remove_image',removeImage.checked?'true':'false');
 const id=editingId.value; const r=await fetch(id?`/api/news/${id}`:'/api/news',{method:id?'PUT':'POST',body:fd});
 if(r.ok){setMessage(formMsg,'저장되었습니다.',true);resetForm();loadNews();}else{const d=await r.json().catch(()=>({detail:'저장 실패'}));setMessage(formMsg,d.detail||'저장 실패');}
};
function esc(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
if(adminKey){loginBox.classList.add('hidden');panel.classList.remove('hidden');loadNews();}
