document.addEventListener('DOMContentLoaded', function() {
    console.log('Carbon Catalog Application loaded');

    // Only fetch if the container exists
    const catalogContainer = document.getElementById('catalog-container');
    if (!catalogContainer) {
        console.error('Catalog container not found');
        return;
    }

    console.log('Fetching entries from API...');
    fetch('/api/random-entries')
        .then(response => {
            console.log('API response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Parsed data:', data);
            if (!data.entries || data.entries.length === 0) {
                console.log('No entries returned from API');
                return;
            }

            // Create a row for the tiles
            const row = document.createElement('div');
            row.className = 'bx--row';
            catalogContainer.appendChild(row);

            // Add tiles using Carbon Design patterns
            data.entries.forEach(entry => {
                const col = document.createElement('div');
                col.className = 'bx--col-lg-4 bx--col-md-6 bx--col-sm-12';

                const tile = document.createElement('div');
                tile.className = 'bx--tile';
                tile.innerHTML = `
                    <h3>${entry.title}</h3>
                    <p class="bx--type-body-long-01">Source: ${entry.description}</p>
                    <img src="${entry.image_url}" alt="${entry.title}" style="max-width:100%; margin:10px 0;">
                    <a href="${entry.url}" target="_blank" class="bx--link">Visit Site</a>
                `;

                col.appendChild(tile);
                row.appendChild(col);
            });
        })
        .catch(error => {
            console.error('Error fetching random entries:', error);
            catalogContainer.innerHTML = `
                <div class="bx--row">
                    <div class="bx--col">
                        <div class="bx--inline-notification bx--inline-notification--error">
                            <div class="bx--inline-notification__details">
                                <h3 class="bx--inline-notification__title">Error loading catalog data</h3>
                                <p class="bx--inline-notification__subtitle">${error.message}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
});
