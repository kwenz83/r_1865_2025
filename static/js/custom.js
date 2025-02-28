let currentCell = null;

document.addEventListener('contextmenu', (e) => {
    if (e.target.classList.contains('editable')) {
        e.preventDefault();
        currentCell = e.target;
        const menu = document.getElementById('contextMenu');
        menu.style.display = 'block';
        menu.style.left = `${e.pageX}px`;
        menu.style.top = `${e.pageY}px`;
    }
});

document.addEventListener('click', () => {
    document.getElementById('contextMenu').style.display = 'none';
});

function handleEdit() {
    if (currentCell) {
        const value = currentCell.innerText;
        currentCell.innerHTML = `<input type="number" value="${value}" 
            style="width:80px" class="form-control">`;
    }
}

function handleUpdate() {
    if (currentCell) {
        const input = currentCell.querySelector('input');
        const value = input ? input.value : currentCell.innerText;

        fetch('/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                member: currentCell.dataset.member,
                date: currentCell.dataset.date,
                distance: value
            })
        }).then(response => response.json())
          .then(data => {
              if (data.status === 'success') {
                  currentCell.classList.add('updated');
                  currentCell.innerHTML = parseFloat(value).toFixed(2);
              } else {
                  alert('更新失败：' + data.message);
              }
          })
          .catch(error => {
              alert('请求失败：' + error.message);
          });
    }
}



// 新增排序功能
document.querySelectorAll('.sortable').forEach(headerCell => {
    headerCell.addEventListener('click', () => {
        const table = headerCell.closest('table')
        const headerIndex = Array.prototype.indexOf.call(
            headerCell.parentElement.children, headerCell
        )
        const currentIsAsc = headerCell.classList.contains('asc')

        // 重置所有排序状态
        document.querySelectorAll('.sortable').forEach(h => {
            h.classList.remove('asc', 'desc')
            h.querySelector('.sort-arrow').className = 'sort-arrow'
        })

        // 设置新排序状态
        const newDir = currentIsAsc ? 'desc' : 'asc'
        headerCell.classList.add(newDir)
        headerCell.querySelector('.sort-arrow').classList.add(newDir)

        // 执行排序
        sortTable(table, headerIndex, newDir, headerCell.dataset.type)
    })
})

function sortTable(table, columnIdx, direction, dataType) {
    const tbody = table.tBodies[0]
    const rows = Array.from(tbody.querySelectorAll('tr'))

    rows.sort((a, b) => {
        const aVal = getCellValue(a, columnIdx)
        const bVal = getCellValue(b, columnIdx)

        if (dataType === 'number') {
            return parseFloat(aVal) - parseFloat(bVal)
        }
        return aVal.localeCompare(bVal)
    })

    if (direction === 'desc') {
        rows.reverse()
    }

    // 重新插入已排序的行
    rows.forEach(row => tbody.appendChild(row))
}

function getCellValue(row, columnIdx) {
    const cell = row.children[columnIdx]
    return cell.querySelector('input') ?
        cell.querySelector('input').value :
        cell.innerText
}

document.getElementById('fileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        fetch('/import', {
            method: 'POST',
            body: formData
        }).then(response => response.json())
          .then(data => {
              if (data.status === 'success') {
                  window.location.reload();
              } else {
                  alert(data.message);
              }
          });
    }
});