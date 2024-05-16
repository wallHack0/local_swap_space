// Listening for the 'submit' event on the login form.
document.getElementById('loginForm').addEventListener('submit', function (event) {
    // Checking if geolocation is available in the user's browser.
    if (navigator.geolocation) {
        // Stopping the default form processing to first fetch geolocation data
        event.preventDefault();

        // Fetching the current geographic coordinates of the user.
        navigator.geolocation.getCurrentPosition(function (position) {
            let latitude = position.coords.latitude;
            let longitude = position.coords.longitude;

            // Creating input elements to store latitude and longitude.
            let hiddenLat = document.createElement('input');
            hiddenLat.setAttribute('type', 'hidden');
            hiddenLat.setAttribute('name', 'latitude');
            hiddenLat.value = latitude;
            // Attaching this element to the login form.
            document.getElementById('loginForm').appendChild(hiddenLat);

            let hiddenLong = document.createElement('input');
            hiddenLong.setAttribute('type', 'hidden');
            hiddenLong.setAttribute('name', 'longitude');
            hiddenLong.value = longitude;
            document.getElementById('loginForm').appendChild(hiddenLong);

            // Resubmitting the form, now with added geographic data.
            document.getElementById('loginForm').submit();

        }, function (error) {
            console.log("Błąd: ", error);
            // Submitting the form even if there are errors related to geolocation.
            document.getElementById('loginForm').submit();
        });
    }
});
