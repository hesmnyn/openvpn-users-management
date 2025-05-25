// admin-copy-cell.js
document.addEventListener('DOMContentLoaded', () => {
    const copyFields = ["username_natural", "openvpn_password", "expiry_date"];
    const table = document.querySelector('#result_list');
    if (!table) return;
  
    // Helper: fallback copy
    function fallbackCopyTextToClipboard(text) {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      // avoid scrolling to bottom
      textArea.style.position = 'fixed';
      textArea.style.top = 0;
      textArea.style.left = 0;
      textArea.style.width = '1px';
      textArea.style.height = '1px';
      textArea.style.padding = 0;
      textArea.style.border = 'none';
      textArea.style.outline = 'none';
      textArea.style.boxShadow = 'none';
      textArea.style.background = 'transparent';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
  
      let successful = false;
      try {
        successful = document.execCommand('copy');
      } catch (err) {
        successful = false;
      }
      document.body.removeChild(textArea);
  
      return successful ? Promise.resolve() : Promise.reject();
    }
  
    // Helper: copy text, with fallback
    function copyText(text) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text);
      }
      return fallbackCopyTextToClipboard(text);
    }
  
    // build field→column index map
    const idxMap = {};
    table.querySelectorAll('thead th').forEach((th, i) => {
      const colClass = Array.from(th.classList).find(c => c.startsWith('column-'));
      if (!colClass) return;
      const fieldName = colClass.replace('column-', '').split(' ')[0];
      if (copyFields.includes(fieldName)) idxMap[fieldName] = i;
    });
  
    // inject buttons
    table.querySelectorAll('tbody tr').forEach(tr => {
      Object.entries(idxMap).forEach(([fieldName, idx]) => {
        const td = tr.children[idx];
        if (!td) return;
  
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = '📋';
        btn.className = 'copy-cell-btn';
        btn.title = 'Copy value';
        btn.style.marginLeft = '4px';
        btn.style.fontSize = '0.8em';
        btn.style.cursor = 'pointer';
  
        btn.addEventListener('click', e => {
          e.stopPropagation();
          // clone+strip for raw text
          const clone = td.cloneNode(true);
          const b = clone.querySelector('.copy-cell-btn');
          if (b) b.remove();
          const raw = clone.innerText.trim();
  
          let textToCopy;
          if (fieldName === 'expiry_date') {
            const parts = raw.match(/^(\w+\.?) (\d{1,2}), (\d{4})$/);
            if (parts) {
                const names = {
                    'Jan.': 1,
                    'Feb.': 2,
                    March: 3,
                    April: 4,
                    May: 5,
                    June: 6,
                    July: 7,
                    'Aug.': 8,
                    'Sept.': 9,
                    'Oct.': 10,
                    'Nov.': 11,
                    'Dec.': 12,
                  };
              const mm = String(names[parts[1]]).padStart(2,'0');
              const dd = String(parts[2]).padStart(2,'0');
              const yyyy = parts[3];
              textToCopy = `Expire Date: ${yyyy}-${mm}-${dd}`;
            } else {
              textToCopy = `Expire Date: ${raw}`;
            }
          } else if (fieldName === 'username_natural') {
            textToCopy = `Username: ${raw}`;
          }
          else if (fieldName === 'openvpn_password') {
            textToCopy = `Password: ${raw}`;
          }else{
            textToCopy = raw;
          }
  
          copyText(textToCopy)
            .then(() => {
              btn.textContent = '✔️';
              setTimeout(() => btn.textContent = '📋', 800);
            })
            .catch(() => {
              // Optionally handle failure (e.g. show an alert)
              console.warn('Copy failed');
            });
        });
  
        // for username, place after the <a>
        if (fieldName === 'username_natural') {
          const link = td.querySelector('a');
          if (link) {
            link.insertAdjacentElement('afterend', btn);
            return;
          }
        }
  
        td.appendChild(btn);
      });
    });
  });
  