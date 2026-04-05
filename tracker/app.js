let weeklyChart = null;

async function loadDashboard() {
    updateGreeting();
    try {
        const [habitsResp, tasksResp, statsResp] = await Promise.all([
            fetchWithAuth('/habits'),
            fetchWithAuth('/tasks'),
            fetchWithAuth('/habits/stats')
        ]);
        const habits = await habitsResp.json();
        const tasks = await tasksResp.json();
        const stats = await statsResp.json();

        renderHabits(habits);
        renderTasks(tasks);
        renderStats(stats);
        renderScoreCards(stats);
        renderChart(stats.weekly_data);
    } catch (err) {
        console.error('Failed to load dashboard:', err);
    }
}

function updateGreeting() {
    const now = new Date();
    const hour = now.getHours();
    let greet = 'Good morning ☀️';
    if (hour >= 12 && hour < 17) greet = 'Good afternoon 🌤️';
    else if (hour >= 17) greet = 'Good evening 🌙';

    document.getElementById('greeting-text').textContent = greet;

    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    const dayName = days[now.getDay()];
    const month = months[now.getMonth()];
    document.getElementById('greeting-date').textContent =
        `${dayName}, ${now.getDate()} ${month} ${now.getFullYear()} · Let's make today count`;
}

function renderScoreCards(stats) {
    const pct = stats.today_total > 0
        ? Math.round((stats.today_done / stats.today_total) * 100) : 0;

    document.getElementById('ring-fill').setAttribute('stroke-dasharray', `${pct}, 100`);
    document.getElementById('ring-text').textContent = `${pct}%`;
    document.getElementById('habits-count').textContent = `${stats.today_done} / ${stats.today_total}`;
    document.getElementById('day-streak').textContent = stats.day_streak;
    document.getElementById('tasks-done').textContent = `${stats.tasks_done} / ${stats.tasks_total}`;
}

function renderHabits(habits) {
    const grid = document.getElementById('habits-grid');
    grid.innerHTML = '';

    habits.forEach(h => {
        const card = document.createElement('div');
        card.className = `habit-card ${h.done_today ? 'done' : ''}`;
        card.innerHTML = `
            <div class="habit-info">
                <span class="habit-emoji">${h.emoji}</span>
                <div>
                    <div class="habit-name">${h.name}</div>
                    <div class="habit-streak">${h.streak}d streak</div>
                </div>
            </div>
            <label class="toggle">
                <input type="checkbox" ${h.done_today ? 'checked' : ''} data-habit-id="${h.id}">
                <span class="toggle-slider"></span>
            </label>
        `;

        const checkbox = card.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', () => toggleHabit(h.id));
        grid.appendChild(card);
    });
}

async function toggleHabit(habitId) {
    try {
        await fetchWithAuth('/habits/log', {
            method: 'POST',
            body: JSON.stringify({ habit_id: habitId })
        });
        loadDashboard();
    } catch (err) {
        console.error('Failed to toggle habit:', err);
    }
}

function renderTasks(tasks) {
    const list = document.getElementById('tasks-list');
    list.innerHTML = '';

    tasks.forEach(t => {
        const item = document.createElement('div');
        item.className = `task-item ${t.is_done ? 'done' : ''}`;
        const priorityColor = { high: '#ef4444', medium: '#eab308', low: '#22c55e' }[t.priority];

        item.innerHTML = `
            <label class="task-check">
                <input type="checkbox" ${t.is_done ? 'checked' : ''} data-task-id="${t.id}">
                <span class="checkmark ${t.is_done ? 'checked' : ''}"></span>
            </label>
            <span class="task-title ${t.is_done ? 'strikethrough' : ''}">${t.title}</span>
            <span class="priority-dot" style="background:${priorityColor}"></span>
            <button class="delete-task-btn" data-task-id="${t.id}">&times;</button>
        `;

        const checkbox = item.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', () => toggleTask(t.id, !t.is_done));

        const deleteBtn = item.querySelector('.delete-task-btn');
        deleteBtn.addEventListener('click', () => deleteTask(t.id));

        list.appendChild(item);
    });
}

async function toggleTask(taskId, isDone) {
    try {
        await fetchWithAuth(`/tasks/update?id=${taskId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_done: isDone })
        });
        loadDashboard();
    } catch (err) {
        console.error('Failed to toggle task:', err);
    }
}

async function deleteTask(taskId) {
    try {
        await fetchWithAuth(`/tasks/delete?id=${taskId}`, { method: 'DELETE' });
        loadDashboard();
    } catch (err) {
        console.error('Failed to delete task:', err);
    }
}

// Add task on Enter
document.getElementById('new-task-input').addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const input = e.target;
    const title = input.value.trim();
    if (!title) return;

    const priority = document.getElementById('new-task-priority').value;
    try {
        await fetchWithAuth('/tasks', {
            method: 'POST',
            body: JSON.stringify({ title, priority })
        });
        input.value = '';
        loadDashboard();
    } catch (err) {
        console.error('Failed to add task:', err);
    }
});

function renderStats(stats) {
    document.getElementById('weekly-avg').textContent = `${stats.weekly_avg}%`;
    document.getElementById('best-day').textContent = stats.best_day ? `Best: ${stats.best_day}` : '—';
    document.getElementById('top-habit').textContent = stats.top_habit || '—';
}

function renderChart(weeklyData) {
    const ctx = document.getElementById('weekly-chart').getContext('2d');

    if (weeklyChart) {
        weeklyChart.destroy();
    }

    const labels = weeklyData.map(d => d.day);
    const data = weeklyData.map(d => d.percentage);

    weeklyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: data.map(v =>
                    v >= 80 ? '#7a9e3e' : v >= 50 ? '#a3b86c' : '#c4cc8a'
                ),
                borderRadius: 6,
                barThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: v => v + '%',
                        color: '#888',
                        stepSize: 20
                    },
                    grid: { color: '#333' }
                },
                x: {
                    ticks: { color: '#888' },
                    grid: { display: false }
                }
            }
        }
    });
}

// Add habit modal
document.getElementById('add-habit-btn').addEventListener('click', () => {
    document.getElementById('habit-modal').style.display = 'flex';
    document.getElementById('habit-name-input').value = '';
    document.getElementById('habit-emoji-input').value = '✅';
    document.querySelectorAll('.emoji-option').forEach(el => el.classList.remove('selected'));
    document.querySelector('.emoji-option[data-emoji="✅"]').classList.add('selected');
});

document.getElementById('habit-cancel-btn').addEventListener('click', () => {
    document.getElementById('habit-modal').style.display = 'none';
});

document.querySelectorAll('.emoji-option').forEach(el => {
    el.addEventListener('click', () => {
        document.querySelectorAll('.emoji-option').forEach(e => e.classList.remove('selected'));
        el.classList.add('selected');
        document.getElementById('habit-emoji-input').value = el.dataset.emoji;
    });
});

document.getElementById('habit-save-btn').addEventListener('click', async () => {
    const name = document.getElementById('habit-name-input').value.trim();
    const emoji = document.getElementById('habit-emoji-input').value;
    if (!name) return;

    try {
        await fetchWithAuth('/habits', {
            method: 'POST',
            body: JSON.stringify({ name, emoji })
        });
        document.getElementById('habit-modal').style.display = 'none';
        loadDashboard();
    } catch (err) {
        console.error('Failed to add habit:', err);
    }
});

// Close modal on backdrop click
document.getElementById('habit-modal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('habit-modal')) {
        document.getElementById('habit-modal').style.display = 'none';
    }
});
