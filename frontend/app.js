// Use relative URL if served from HTTP server, full URL if opened as file
const API_URL = window.location.protocol === 'file:' 
    ? 'http://127.0.0.1:62515/dj'
    : '/dj';

// DOM Elements
const promptInput = document.getElementById('promptInput');
const searchBtn = document.getElementById('searchBtn');
const welcomeScreen = document.getElementById('welcomeScreen');
const loadingScreen = document.getElementById('loadingScreen');
const resultsScreen = document.getElementById('resultsScreen');
const errorScreen = document.getElementById('errorScreen');
const errorMessage = document.getElementById('errorMessage');
const playlistTitle = document.getElementById('playlistTitle');
const playlistMeta = document.getElementById('playlistMeta');
const songsList = document.getElementById('songsList');

// Event Listeners
searchBtn.addEventListener('click', handleSearch);
promptInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

// Suggestion chips
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const prompt = chip.getAttribute('data-prompt');
        promptInput.value = prompt;
        handleSearch();
    });
});

async function handleSearch() {
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        alert('Please enter a prompt');
        return;
    }

    // Show loading screen
    showScreen('loading');

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: prompt })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to fetch recommendations');
        }

        displayResults(data);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
    }
}

function displayResults(data) {
    // Update playlist title and meta
    playlistTitle.textContent = formatPrompt(data.prompt);
    const songCount = data.queue.length;
    const prefs = data.preferences;
    const prefsText = `${prefs.genre} • ${prefs.mood} • ${prefs.energy} energy • ${prefs.tempo} tempo`;
    playlistMeta.textContent = `${songCount} songs • ${prefsText}`;

    // Clear previous songs
    songsList.innerHTML = '';

    // Find max score for percentage calculation (use actual max from queue, fallback to 7)
    const scores = data.queue.map(song => song.score);
    const maxScore = scores.length > 0 ? Math.max(...scores) : 7;

    // Add songs to list
    data.queue.forEach((song, index) => {
        const songRow = createSongRow(song, index + 1, maxScore);
        songsList.appendChild(songRow);
    });

    showScreen('results');
}

function createSongRow(song, index, maxScore) {
    const row = document.createElement('div');
    row.className = 'song-row';

    // Calculate match percentage based on actual max score
    // Handle decimal scores properly and cap at 100%
    const score = parseFloat(song.score) || 0;
    const max = parseFloat(maxScore) || 1;
    
    // Calculate percentage, ensuring it doesn't exceed 100%
    let matchPercentage = Math.round((score / max) * 100);
    matchPercentage = Math.min(100, Math.max(0, matchPercentage)); // Cap between 0-100
    
    // Calculate bar width, also capped at 100%
    const matchBarWidth = Math.min(100, Math.max(20, (score / max) * 100));

    row.innerHTML = `
        <div class="song-index-container">
            <div class="song-index">${index}</div>
            <div class="play-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </div>
        </div>
        <div class="song-title-col">
            <div class="song-title">${escapeHtml(song.song)}</div>
        </div>
        <div class="song-artist-col">
            <div class="song-artist">${escapeHtml(song.artist)}</div>
        </div>
        <div class="song-match">
            <div class="match-bar">
                <div class="match-bar-fill" style="width: ${matchBarWidth}%"></div>
                <span>${matchPercentage}%</span>
            </div>
        </div>
    `;

    return row;
}

function showScreen(screen) {
    welcomeScreen.classList.add('hidden');
    loadingScreen.classList.add('hidden');
    resultsScreen.classList.add('hidden');
    errorScreen.classList.add('hidden');

    switch(screen) {
        case 'welcome':
            welcomeScreen.classList.remove('hidden');
            // Keep search bar visible on welcome screen
            document.querySelector('.header').style.display = 'block';
            break;
        case 'loading':
            loadingScreen.classList.remove('hidden');
            document.querySelector('.header').style.display = 'block';
            break;
        case 'results':
            resultsScreen.classList.remove('hidden');
            // Keep search bar visible on results
            document.querySelector('.header').style.display = 'block';
            break;
        case 'error':
            errorScreen.classList.remove('hidden');
            document.querySelector('.header').style.display = 'block';
            break;
    }
}

function showError(message) {
    errorMessage.textContent = message;
    showScreen('error');
}

function resetToWelcome() {
    showScreen('welcome');
    promptInput.value = '';
}

function formatPrompt(prompt) {
    // Capitalize first letter of each word
    return prompt
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}