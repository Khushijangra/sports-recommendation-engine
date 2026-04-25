/**
 * Sports Recommendation System - Enhanced Frontend
 * Displays science-backed recommendations with evidence
 */

// State
let selectedStudent = null;
let selectedPreferences = [];

// Sports list for preferences
const SPORTS_LIST = [
    'Archery', 'Athletics', 'Badminton', 'Basketball', 'Boxing',
    'Cycling', 'Fencing', 'Football', 'Gymnastics', 'Hockey',
    'Judo', 'Kabaddi', 'Kho-Kho', 'Shooting', 'Swimming',
    'Table Tennis', 'Tennis', 'Volleyball', 'Weightlifting', 'Wrestling'
];

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
const resultsContainer = document.getElementById('resultsContainer');
const emptyState = document.getElementById('emptyState');
const statsBar = document.getElementById('stats');
const preferencesSection = document.getElementById('preferencesSection');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    setupSearch();
    setupPreferences();
});

// Load stats
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        statsBar.innerHTML = `
            <span class="stat-item"><strong>${stats.total_students.toLocaleString()}</strong> Students</span>
            <span class="stat-item"><strong>${stats.schools}</strong> Schools</span>
            <span class="stat-item"><strong>${stats.sports_count}</strong> Sports</span>
            <span class="stat-item">Age: <strong>${stats.age_range[0]}-${stats.age_range[1]}</strong> yrs</span>
            <span class="stat-item methodology">📊 ${stats.methodology}</span>
        `;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Setup search
function setupSearch() {
    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        if (query.length < 2) {
            hideSearchResults();
            return;
        }

        debounceTimer = setTimeout(() => searchStudents(query), 300);
    });

    searchInput.addEventListener('focus', () => {
        if (searchInput.value.length >= 2) {
            searchResults.classList.remove('hidden');
        }
    });

    document.addEventListener('click', (e) => {
        if (!searchResults.contains(e.target) && e.target !== searchInput) {
            hideSearchResults();
        }
    });
}

async function searchStudents(query) {
    try {
        const response = await fetch(`/api/students/search?q=${encodeURIComponent(query)}&limit=20`);
        const students = await response.json();

        if (students.length === 0) {
            searchResults.innerHTML = '<div class="search-result-item">No students found</div>';
        } else {
            searchResults.innerHTML = students.map(s => `
                <div class="search-result-item" onclick="selectStudent('${s.id}')">
                    <span class="result-name">${s.name}</span>
                    <span class="result-meta">${s.class} • ${s.age}y • ${s.gender}</span>
                </div>
            `).join('');
        }

        searchResults.classList.remove('hidden');
    } catch (error) {
        console.error('Search failed:', error);
    }
}

function hideSearchResults() {
    searchResults.classList.add('hidden');
}

async function selectStudent(studentId) {
    hideSearchResults();
    searchInput.value = 'Loading...';

    try {
        const response = await fetch(`/api/recommend/${studentId}`);
        const data = await response.json();

        if (data.error) {
            alert('Student not found');
            searchInput.value = '';
            return;
        }

        selectedStudent = data;
        searchInput.value = data.student_name;

        displayResults(data);
    } catch (error) {
        console.error('Failed to get recommendations:', error);
        alert('Failed to load recommendations');
        searchInput.value = '';
    }
}

function displayResults(data) {
    emptyState.classList.add('hidden');
    resultsContainer.classList.remove('hidden');
    showPreferencesSection();

    // Update student info with height percentile
    document.getElementById('studentName').textContent = data.student_name;

    let detailsText = `${data.class} • ${data.age} years • ${data.gender}`;
    if (data.height_cm) {
        detailsText += ` • ${data.height_cm}cm`;
        if (data.height_percentile) {
            detailsText += ` (${Math.round(data.height_percentile)}th %ile)`;
        }
    }
    if (data.bmi) {
        detailsText += ` • BMI: ${data.bmi}`;
    }
    document.getElementById('studentDetails').textContent = detailsText;

    document.getElementById('studentAvatar').textContent =
        data.gender === 'Male' ? '👨‍🎓' : '👩‍🎓';

    displayScores(data.scores);
    drawRadarChart(data.scores);
    displayRecommendations(data.recommendations);
}

function displayScores(scores) {
    const scoresGrid = document.getElementById('scoresGrid');

    const scoreItems = Object.entries(scores)
        .filter(([key]) => key !== 'Overall')
        .map(([name, value]) => {
            const percent = (value / 10) * 100;
            let level = 'low';
            if (value >= 7) level = 'high';
            else if (value >= 5) level = 'medium';

            return `
                <div class="score-item">
                    <div class="score-label">
                        <span class="score-name">${name}</span>
                        <span class="score-value">${value.toFixed(1)}</span>
                    </div>
                    <div class="score-bar">
                        <div class="score-fill ${level}" style="width: ${percent}%"></div>
                    </div>
                </div>
            `;
        }).join('');

    scoresGrid.innerHTML = scoreItems;
}

function drawRadarChart(scores) {
    const canvas = document.getElementById('radarChart');
    const ctx = canvas.getContext('2d');

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const labels = Object.keys(scores).filter(k => k !== 'Overall');
    const values = labels.map(l => scores[l]);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 40;
    const numPoints = labels.length;
    const angleStep = (2 * Math.PI) / numPoints;

    // Draw grid
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.2)';
    ctx.lineWidth = 1;

    for (let i = 2; i <= 10; i += 2) {
        ctx.beginPath();
        const r = (radius * i) / 10;
        ctx.arc(centerX, centerY, r, 0, 2 * Math.PI);
        ctx.stroke();
    }

    // Draw axes
    for (let i = 0; i < numPoints; i++) {
        const angle = i * angleStep - Math.PI / 2;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(
            centerX + radius * Math.cos(angle),
            centerY + radius * Math.sin(angle)
        );
        ctx.stroke();
    }

    // Draw data polygon
    ctx.beginPath();
    ctx.fillStyle = 'rgba(16, 185, 129, 0.3)';
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;

    for (let i = 0; i < numPoints; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const value = values[i] / 10;
        const x = centerX + radius * value * Math.cos(angle);
        const y = centerY + radius * value * Math.sin(angle);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }

    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Draw points
    ctx.fillStyle = '#10b981';
    for (let i = 0; i < numPoints; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const value = values[i] / 10;
        const x = centerX + radius * value * Math.cos(angle);
        const y = centerY + radius * value * Math.sin(angle);

        ctx.beginPath();
        ctx.arc(x, y, 5, 0, 2 * Math.PI);
        ctx.fill();
    }

    // Draw labels
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (let i = 0; i < numPoints; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const labelRadius = radius + 25;
        const x = centerX + labelRadius * Math.cos(angle);
        const y = centerY + labelRadius * Math.sin(angle);

        ctx.fillText(labels[i], x, y);
    }
}

function displayRecommendations(recs) {
    const list = document.getElementById('recommendationsList');

    // Handle new 3-tier format
    if (recs.tier1_best_match) {
        list.innerHTML = `
            ${renderTier('🏆 Best Match Now', 'tier1', recs.tier1_best_match,
            'Sports that match your current abilities')}
            ${renderTier('📈 Growth Potential', 'tier2', recs.tier2_potential,
                'Sports you could excel at with development')}
            ${renderTier('🌱 Entry Sports', 'tier3', recs.tier3_entry,
                    'Age-appropriate starting points')}
            ${recs.sports_avoided && recs.sports_avoided.length > 0 ?
                `<div class="age-note">
                    <strong>Age Group:</strong> ${recs.age_group.replace('_', ' ')}
                    • Avoiding: ${recs.sports_avoided.join(', ')} (not age-appropriate)
                </div>` : ''}
        `;
    } else {
        // Fallback to old format
        list.innerHTML = recs.map((rec, index) => renderOldCard(rec, index)).join('');
    }
}

function renderTier(title, tierClass, sports, description) {
    if (!sports || sports.length === 0) {
        return `
            <div class="tier-section ${tierClass}">
                <div class="tier-header">
                    <h3>${title}</h3>
                    <p class="tier-desc">${description}</p>
                </div>
                <div class="tier-empty">No recommendations for this tier</div>
            </div>
        `;
    }

    return `
        <div class="tier-section ${tierClass}">
            <div class="tier-header">
                <h3>${title}</h3>
                <p class="tier-desc">${description}</p>
            </div>
            <div class="tier-cards">
                ${sports.map((sport, idx) => renderTierCard(sport, tierClass, idx)).join('')}
            </div>
        </div>
    `;
}

function renderTierCard(sport, tierClass, index) {
    const emoji = getSportEmoji(sport.sport);

    if (tierClass === 'tier1') {
        return `
            <div class="tier-card ${tierClass}-card">
                <div class="tier-rank">#${index + 1}</div>
                <div class="tier-sport">
                    <span class="sport-emoji">${emoji}</span>
                    <span class="sport-name">${sport.sport}</span>
                </div>
                <div class="tier-details">
                    <span class="sport-type-badge">${sport.type || ''}</span>
                    <div class="tier-score">${sport.score}/10</div>
                </div>
                <div class="tier-reason">${sport.reason || ''}</div>
            </div>
        `;
    } else if (tierClass === 'tier2') {
        return `
            <div class="tier-card ${tierClass}-card">
                <div class="tier-sport">
                    <span class="sport-emoji">${emoji}</span>
                    <span class="sport-name">${sport.sport}</span>
                </div>
                <div class="tier-details">
                    <span class="current-score">Current: ${sport.current_score}/10</span>
                    <span class="potential-badge">Potential: +${sport.potential_score}</span>
                </div>
                <div class="improve-areas">
                    ${sport.improve_areas ?
                `<span class="improve-label">Work on:</span> 
                         ${sport.improve_areas.map(a => `<span class="improve-tag">${a}</span>`).join('')}`
                : ''}
                </div>
            </div>
        `;
    } else {
        return `
            <div class="tier-card ${tierClass}-card">
                <div class="tier-sport">
                    <span class="sport-emoji">${emoji}</span>
                    <span class="sport-name">${sport.sport}</span>
                </div>
                <div class="tier-details">
                    <div class="tier-score">${sport.score}/10</div>
                </div>
                <div class="leads-to">
                    ${sport.leads_to && sport.leads_to.length > 0 ?
                `<span class="leads-label">Leads to:</span> 
                         ${sport.leads_to.map(s => `<span class="leads-tag">${s}</span>`).join('')}`
                : `<span class="leads-label">Foundational sport</span>`}
                </div>
            </div>
        `;
    }
}

function renderOldCard(rec, index) {
    return `
        <div class="recommendation-card">
            <div class="rank-badge">#${rec.rank}</div>
            <div class="rec-content">
                <h3>${getSportEmoji(rec.sport)} ${rec.sport}</h3>
                <p>${rec.description || rec.reason || ''}</p>
            </div>
            <div class="rec-score">
                <div class="score-circle" style="--percent: ${rec.score * 10}%">
                    <div class="score-inner">${rec.score}</div>
                </div>
            </div>
        </div>
    `;
}

function getSportEmoji(sport) {
    const emojis = {
        'Archery': '🎯',
        'Athletics': '🏃',
        'Badminton': '🏸',
        'Basketball': '🏀',
        'Boxing': '🥊',
        'Cycling': '🚴',
        'Fencing': '⚔️',
        'Football': '⚽',
        'Gymnastics': '🤸',
        'Hockey': '🏑',
        'Judo': '🥋',
        'Kabaddi': '🤼',
        'Kho-Kho': '🏃‍♀️',
        'Shooting': '🎯',
        'Swimming': '🏊',
        'Table Tennis': '🏓',
        'Tennis': '🎾',
        'Volleyball': '🏐',
        'Weightlifting': '🏋️',
        'Wrestling': '🤼‍♂️'
    };
    return emojis[sport] || '🏆';
}

// ============================================
// PREFERENCES FUNCTIONALITY
// ============================================

function setupPreferences() {
    // Populate preferences list
    const prefList = document.getElementById('preferencesList');
    if (!prefList) return;

    prefList.innerHTML = SPORTS_LIST.map(sport => `
        <label class="pref-item">
            <input type="checkbox" value="${sport}" onchange="togglePreference('${sport}')">
            <span class="pref-emoji">${getSportEmoji(sport)}</span>
            <span class="pref-name">${sport}</span>
        </label>
    `).join('');

    // Apply button
    const applyBtn = document.getElementById('applyPreferences');
    if (applyBtn) {
        applyBtn.addEventListener('click', applyPreferences);
    }
}

function togglePreference(sport) {
    if (selectedPreferences.includes(sport)) {
        selectedPreferences = selectedPreferences.filter(s => s !== sport);
    } else {
        selectedPreferences.push(sport);
    }
}

async function applyPreferences() {
    if (!selectedStudent) return;

    const studentId = selectedStudent.student_id;
    const prefsParam = selectedPreferences.join(',');

    try {
        const response = await fetch(`/api/recommend/${studentId}?preferences=${encodeURIComponent(prefsParam)}`);
        const data = await response.json();

        if (!data.error) {
            selectedStudent = data;
            displayResults(data);
        }
    } catch (error) {
        console.error('Failed to apply preferences:', error);
    }
}

function showPreferencesSection() {
    const prefSection = document.getElementById('preferencesSection');
    if (prefSection) {
        prefSection.classList.remove('hidden');
    }
}
