// Nasłuchiwanie zdarzenia 'submit' na formularzu logowania.
document.getElementById('loginForm').addEventListener('submit', function (event) {
    // Sprawdzenie, czy geolokalizacja jest dostępna w przeglądarce użytkownika.
    if (navigator.geolocation) {
        // Zatrzymanie domyślnego przetwarzania formularza, aby najpierw pobrać dane geolokalizacyjne.
        event.preventDefault();

        // Pobiera aktualne współrzędne geograficzne użytkownika.
        navigator.geolocation.getCurrentPosition(function (position) {
            let latitude = position.coords.latitude;
            let longitude = position.coords.longitude;

            // Stworzenie elementów input, które będą przechowywać szerokość i długość geograficzną.
            let hiddenLat = document.createElement('input');
            hiddenLat.setAttribute('type', 'hidden');
            hiddenLat.setAttribute('name', 'latitude');
            hiddenLat.value = latitude;
            // Dołączenie tego elementu do formularza logowania.
            document.getElementById('loginForm').appendChild(hiddenLat);

            let hiddenLong = document.createElement('input');
            hiddenLong.setAttribute('type', 'hidden');
            hiddenLong.setAttribute('name', 'longitude');
            hiddenLong.value = longitude;
            document.getElementById('loginForm').appendChild(hiddenLong);

            // Ponowne przesłanie formularza, teraz z dodanymi danymi geograficznymi.
            document.getElementById('loginForm').submit();

        }, function (error) {
            console.log("Błąd: ", error);
            // Przesłanie formularza mimo błędów związanych z lokalizacją.
            document.getElementById('loginForm').submit();
        });
    }
});
