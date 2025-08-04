// Monaco Editor Initialization
require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.33.0/min/vs' } });

require(['vs/editor/editor.main'], function () {
    const editor = monaco.editor.create(document.getElementById('editor-container'), {
        value: [
            '# کد پایتون خود را در اینجا بنویسید',
            'def hello_world():',
            '    print("Hello, Monaco Editor!")',
            '',
            'hello_world()',
            '# یک خطای نمونه:',
            'x = 1 / 0'
        ].join('\\n'),
        language: 'python',
        theme: 'vs-dark', // Dark theme
        lineNumbers: 'on', // Show line numbers
        minimap: {
            enabled: true // Enable minimap
        },
        automaticLayout: true, // Adjust layout on container resize
        suggestOnTriggerCharacters: true, // Enable suggestions
        "semanticHighlighting.enabled": true,
    });

    // Simple terminal simulation
    const terminalInput = document.querySelector('#terminal input');
    terminalInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            const command = terminalInput.value;
            const output = document.createElement('p');
            output.textContent = `> ${command}`;

            const response = document.createElement('p');
            if (command.trim() === 'run') {
                response.textContent = 'اجرای کد... (شبیه‌سازی شده)';
                response.className = 'text-yellow-400';
            } else {
                response.textContent = `دستور '${command}' یافت نشد.`;
                response.className = 'text-red-400';
            }

            const terminalHistory = document.querySelector('#terminal');
            terminalHistory.insertBefore(output, terminalInput.parentElement);
            terminalHistory.insertBefore(response, terminalInput.parentElement);

            terminalInput.value = '';
            terminalHistory.scrollTop = terminalHistory.scrollHeight;
        }
    });

    // Search functionality
    const searchBox = document.getElementById('search-box');
    searchBox.addEventListener('input', function() {
        const filter = searchBox.value.toLowerCase();
        const cards = document.querySelectorAll('#card-container .card');
        cards.forEach(card => {
            const text = card.textContent.toLowerCase();
            if (text.includes(filter)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    });
});
