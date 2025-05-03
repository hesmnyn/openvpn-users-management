// admin-copy-cell.js
document.addEventListener("DOMContentLoaded", () => {
  // Fields we want copy-buttons for
  const copyFields = ["username_natural", "openvpn_password", "expiry_date"];

  const table = document.querySelector("#result_list");
  if (!table) return;

  // Build a map of fieldName → column index
  const idxMap = {};
  table.querySelectorAll("thead th").forEach((th, i) => {
    const colClass = Array.from(th.classList).find((c) =>
      c.startsWith("column-")
    );
    if (!colClass) return;
    const fieldName = colClass.replace("column-", "").split(" ")[0];
    if (copyFields.includes(fieldName)) {
      idxMap[fieldName] = i;
    }
  });

  // Walk each row and inject
  table.querySelectorAll("tbody tr").forEach((tr) => {
    Object.entries(idxMap).forEach(([fieldName, idx]) => {
      const td = tr.children[idx];
      if (!td) return;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "📋";
      btn.className = "copy-cell-btn";
      btn.title = "Copy value";
      btn.style.marginLeft = "4px";
      btn.style.fontSize = "0.8em";
      btn.style.cursor = "pointer";

      btn.addEventListener("click", (e) => {
        e.stopPropagation();

        // clone & strip button so we only get the cell text
        const clone = td.cloneNode(true);
        const b = clone.querySelector(".copy-cell-btn");
        if (b) b.remove();
        const raw = clone.innerText.trim();

        let textToCopy;
        if (fieldName === "expiry_date") {
          // manually parse Month Day, Year
          const mnames = {
            Jan: 1,
            Feb: 2,
            March: 3,
            April: 4,
            May: 5,
            June: 6,
            July: 7,
            Aug: 8,
            Sept: 9,
            Oct: 10,
            Nov: 11,
            Dec: 12,
          };
          const parts = raw.match(/^(\w+) (\d{1,2}), (\d{4})$/);
          if (parts) {
            const month = String(mnames[parts[1]]).padStart(2, "0");
            const day = String(parts[2]).padStart(2, "0");
            const year = parts[3];
            textToCopy = `Expire Date: ${year}-${month}-${day}`;
          } else {
            // fallback if parsing fails
            textToCopy = `Expire Date: ${raw}`;
          }
        } else {
          textToCopy = raw;
        }

        navigator.clipboard.writeText(textToCopy).then(() => {
          btn.textContent = "✔️";
          setTimeout(() => (btn.textContent = "📋"), 800);
        });
      });

      // Username link special-case
      if (fieldName === "username") {
        const link = td.querySelector("a");
        if (link) {
          link.insertAdjacentElement("afterend", btn);
          return;
        }
      }

      // Default: append to end of <td>
      td.appendChild(btn);
    });
  });
});
