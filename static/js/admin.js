// 显示添加用户模态框
function showAddUserModal() {
    document.getElementById('addUserModal').style.display = 'block';
}

// 显示编辑用户模态框
function showEditModal(userId) {
    fetch(`/admin/users/${userId}`)
        .then(response => response.json())
        .then(user => {
            document.getElementById('editUsername').value = user.username;
            document.getElementById('editEmail').value = user.email;
            document.getElementById('editRole').value = user.role;
            document.getElementById('editUserModal').style.display = 'block';
        })
        .catch(error => console.error('Error:', error));
}

// 隐藏模态框
function hideModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// 确认删除用户
function confirmDelete(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        fetch(`/admin/users/${userId}`, {
            method: 'DELETE',
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Failed to delete, please try again');
            }
        })
        .catch(error => console.error('Error:', error));
    }
}

// 关闭模态框当点击外部区域时
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    // 初始化 AOS
    AOS.init({
        duration: 800,
        once: true
    });
}); 