// Page views, Buy-button clicks, and on leave: visible seconds, scroll depth, sections reached, FAQs opened -> Supabase (insert-only table, publishable key). No cookies.
(function(){
  if(navigator.webdriver||!/aicareerfirewall\.com$/.test(location.hostname))return;
  var URL='https://hixdlykszbcerlccvhkq.supabase.co/rest/v1/cf_site_events';
  var KEY='sb_publishable_g1BwX7tVmmASdvo28HgCyQ_CZHKMXM6';
  var vid;
  try{vid=localStorage.getItem('cf_vid');if(!vid){vid=Math.random().toString(36).slice(2,12);localStorage.setItem('cf_vid',vid);}}catch(e){}
  var utm=new URLSearchParams(location.search).get('utm_source');
  function send(kind,target,extra){
    var row={kind:kind,path:location.pathname.slice(0,200),target:target||null,
      referrer:(document.referrer||'').slice(0,300)||null,utm_source:utm?utm.slice(0,80):null,
      visitor:vid||null,mobile:matchMedia('(max-width:700px)').matches};
    for(var k in extra)row[k]=extra[k];
    try{fetch(URL,{method:'POST',keepalive:true,headers:{'apikey':KEY,'Content-Type':'application/json','Prefer':'return=minimal'},
      body:JSON.stringify(row)}).catch(function(){});}catch(e){}
  }
  // Engagement: count only time the tab is visible; report cumulative totals each time it is hidden.
  var shown=Date.now(),secs=0,scroll=0,seen={},faq={};
  function depth(){var h=document.documentElement.scrollHeight-innerHeight;
    scroll=Math.max(scroll,h>0?Math.round(Math.min(1,scrollY/h)*100):100);}
  addEventListener('scroll',depth,{passive:true});depth();
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)seen[e.target.dataset.cfLabel]=1;});},{threshold:0.4});
    document.querySelectorAll('main section').forEach(function(sec,i){sec.dataset.cfLabel=sec.id||('s'+(i+1));io.observe(sec);});
  }
  document.querySelectorAll('details').forEach(function(d){d.addEventListener('toggle',function(){
    if(d.open)faq[d.querySelector('summary').textContent.trim().slice(0,40)]=1;});});
  document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){send('copy_sample',b.dataset.copy);});});
  document.addEventListener('visibilitychange',function(){
    if(document.visibilityState==='hidden'){
      secs+=(Date.now()-shown)/1000;
      send('leave',null,{seconds:Math.min(86400,Math.round(secs)),scroll_pct:scroll,
        sections:Object.keys(seen).join(',').slice(0,200)||null,faq:Object.keys(faq).join(' | ').slice(0,400)||null});
    }else shown=Date.now();
  });
  send('view');
  document.querySelectorAll('a[href*="buy.stripe.com"]').forEach(function(a){
    a.addEventListener('click',function(){send('buy_click',a.href.split('/').pop());});
  });
})();
