// Simple carousel and poem text animation
(function(){
  // Poem text line-by-line animation
  const poem = document.getElementById('poemText');
  if(poem){
    const lines = poem.textContent.split('\n');
    poem.textContent = '';
    lines.forEach((line, i)=>{
      const span = document.createElement('span');
      span.textContent = (i>0?'\n':'') + line;
      span.style.display = 'inline';
      span.className = 'line';
      span.style.opacity = '0';
      span.style.transform = 'translateY(6px)';
      poem.appendChild(span);
    });
    const spans = poem.querySelectorAll('.line');
    spans.forEach((s, i)=>{
      setTimeout(()=>{
        s.style.transition = 'opacity .5s ease, transform .5s ease';
        s.style.opacity = '1';
        s.style.transform = 'translateY(0)';
      }, 80 * i);
    });
  }
})();
