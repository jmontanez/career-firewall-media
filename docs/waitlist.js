// Email signups (Pro waitlist, free kit): inserts an email into Supabase (insert-only table, publishable key).
(function(){
  var URL='https://hixdlykszbcerlccvhkq.supabase.co/rest/v1/cf_waitlist';
  var KEY='sb_publishable_g1BwX7tVmmASdvo28HgCyQ_CZHKMXM6';
  document.querySelectorAll('form.waitlist').forEach(function(f){
    var msg=f.querySelector('.wl-msg'), btn=f.querySelector('button');
    f.addEventListener('submit',function(e){
      e.preventDefault();
      var email=f.email.value.trim(), soon=f.querySelector('[name=soon]');
      btn.disabled=true; msg.textContent='Adding you...';
      fetch(URL,{method:'POST',headers:{'apikey':KEY,'Content-Type':'application/json','Prefer':'return=minimal'},
        body:JSON.stringify({email:email,product:f.dataset.product||'interview-pro',source:f.dataset.source,interviewing_soon:soon?soon.checked:null})})
      .then(function(r){
        if(r.ok||r.status===409){f.reset();
          var kit=f.dataset.reveal&&document.getElementById(f.dataset.reveal);
          if(kit){kit.hidden=false;msg.textContent="Here it is. Scroll down.";kit.scrollIntoView({behavior:'smooth'});}
          else msg.textContent="You're on the list. I'll email you first when Pro opens.";}
        else if(r.status===400){msg.textContent='That email looks off. Try again?';}
        else{msg.textContent="Something went wrong. Email theaicareerfirewall@gmail.com and I'll add you.";}
      })
      .catch(function(){msg.textContent="Something went wrong. Email theaicareerfirewall@gmail.com and I'll add you.";})
      .finally(function(){btn.disabled=false;});
    });
  });
})();
