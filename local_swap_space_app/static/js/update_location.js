document.addEventListener('DOMContentLoaded', function() {
    // Get the form element
    const updateLocationForm = document.getElementById('update-location-form');

    // Add event listener to the button directly within the form
    updateLocationForm.querySelector('#update-location-btn').addEventListener('click', function() {
        // Check if geolocation is supported
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(updateLocation, handleError);
        } else {
            alert("Geolocation is not supported by this browser.");
        }
    });

    function updateLocation(position) {
        // Get the CSRF token from the form
        const csrfToken = updateLocationForm.querySelector('[name=csrfmiddlewaretoken]').value;
        // Get the latitude and longitude from the geolocation API
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        // Update the hidden input fields in the form
        updateLocationForm.querySelector('#latitude').value = latitude;
        updateLocationForm.querySelector('#longitude').value = longitude;

        // Submit the form using the Fetch API
        fetch(updateLocationForm.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                latitude: latitude,
                longitude: longitude
            })
        })
        .then(response => {
            if (response.ok) {
                window.location.href = '/dashboard/';
            } else {
                response.json().then(data => {
                    alert(data.error || 'Error updating location.');
                });
            }
        })
        .catch(error => console.error('Error:', error));
    }

    function handleError(error) {
        console.warn(`ERROR(${error.code}): ${error.message}`);
    }
});
