const list = document.getElementById('newsList');
const liked = new Set(JSON.parse(localStorage.getItem('likedNews') || '[]'));
function saveLiked(){localStorage.setItem('likedNews', JSON.stringify([...liked]));}
async function load(){
  list.innerHTML='<div class="loading">뉴스를 불러오는 중...</div>';
  try{
    const r=await fetch('/api/news'); const data=await r.json();
    if(!data.length){list.innerHTML='<div class="empty">아직 등록된 뉴스가 없습니다.</div>';return;}
    list.innerHTML=data.map(n=>`<article class="news-card">
      ${n.image_url?`<img class="news-image" src="${n.image_url}" alt="">`:''}
      <div class="news-body"><h2 class="news-title">${escapeHtml(n.title)}</h2><div class="news-date">${n.created_at}</div>
      <div class="news-content">${escapeHtml(n.content)}</div>
      <div class="like-row"><button class="like-btn ${liked.has(n.id)?'liked':''}" onclick="likeNews(${n.id},this)">❤️ <span>${n.likes}</span></button></div></div>
    </article>`).join('');
  }catch(e){list.innerHTML='<div class="empty">뉴스를 불러오지 못했습니다.</div>';}
}
async function likeNews(id,btn){
  if(liked.has(id))return;
  const r=await fetch(`/api/news/${id}/like`,{method:'POST'}); if(!r.ok)return;
  const d=await r.json(); liked.add(id); saveLiked(); btn.classList.add('liked'); btn.querySelector('span').textContent=d.likes;
}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
load();
