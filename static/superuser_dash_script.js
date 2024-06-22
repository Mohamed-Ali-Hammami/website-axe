function trainModel() {
    fetch('/superuser/train_model', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})  // Optionally, you can pass data if needed
    })
   .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
   .then(data => {
        console.log('Received data:', data);
        if (data.error) {
            throw new Error(data.error); // Handle specific error messages from backend
        }
        alert('Model trained successfully!');
        displayModelStatistics(data.model_statistics);
        displayModelPlots(data.plot_data);
        showContainer('modelTrainingContainer'); // Show the model training container
    })
   .catch(error => {
        console.error('Error initiating model training:', error);
        alert('An error occurred while initiating model training. Please try again later.');
    });
}
function displayModelStatistics(modelStatistics) {
    const modelStatisticsContainer = document.getElementById('modelStatistics');
    modelStatisticsContainer.innerHTML = `
        <a href="/about_ai" class="button">À propos de L' IA</a>
        <br>
        <p><strong>Erreur Quadratique Moyenne (EQM):</strong> ${modelStatistics.mse.toFixed(2)}</p>
        <p><strong>Erreur Quadratique Moyenne Racine (EQMR):</strong> ${modelStatistics.rmse.toFixed(2)}</p>
        <p><strong>Coefficient de Détermination (R2):</strong> ${modelStatistics.r2.toFixed(2)}</p>
    `;
}

function displayModelPlots(plotData) {
    const modelPlotsContainer = document.getElementById('modelPlots');
    modelPlotsContainer.innerHTML = `
        <p><strong>Distribution of Approval Time:</strong></p>
        <img src="data:image/png;base64,${plotData.distribution}" alt="Approval Time Distribution">
    `;
}

function showContainer(containerId) {
    // Hide all containers
    const containers = document.querySelectorAll('.scrollable-container');
    containers.forEach(container => container.classList.add('hidden'));

    // Show the selected container
    const selectedContainer = document.getElementById(containerId);
    if (selectedContainer) {
        selectedContainer.classList.remove('hidden');
    } else {
        console.error(`Container with ID "${containerId}" not found`);
    }
}

function fetchUserTransactions(userId) {
    fetch(`/user_transactions/${userId}`)
        .then(response => response.json())
        .then(data => {
            const transactionDetailsContainer = document.getElementById('transactionDetailsContainer');
            const transactionDetails = document.getElementById('transactionDetails');
            transactionDetails.innerHTML = ''; // Clear previous details

            data.transactions.forEach(transaction => {
                // Parse ISO 8601 date string into Date object
                const transactionDate = new Date(transaction.transaction_date);
                
                const transactionElement = document.createElement('div');
                transactionElement.classList.add('transaction-item');
                
                // Determine the status class and text
                let statusClass = '';
                let statusText = '';
                if (transaction.status === 'pending') {
                    statusClass = 'pending-text'; 
                    statusText = 'Pending';
                } else {
                    statusClass = 'confirmed-text'; 
                    statusText = transactionDate.toLocaleString('fr-FR', {
                        day: 'numeric',
                        month: 'numeric',
                        year: 'numeric',
                        hour: 'numeric',
                        minute: 'numeric',
                        second: 'numeric'
                    });
                }
                
                transactionElement.innerHTML = `
                    <p>Transaction ID: ${transaction.transaction_id}</p>
                    <p>Sender ID: ${transaction.sender_id}</p>
                    <p>Recipient ID: ${transaction.recipient_id}</p>
                    <p>Amount: ${transaction.amount}</p>
                    <p>Transaction Type: ${transaction.transaction_type}</p>
                    <p>Status: <span class="${statusClass}">${statusText}</span></p>
                    <p>Transaction Date: ${transactionDate.toLocaleString()}</p> <!-- Format date to locale-specific string -->
                    <button class="button" onclick="approveTransaction('${transaction.transaction_id}')">Approve</button>
                `;

                // Check if transaction is confirmed, then hide the button
                if (transaction.status !== 'pending') {
                    const approveButton = transactionElement.querySelector('button');
                    approveButton.style.display = 'none';
                }

                transactionDetails.appendChild(transactionElement);
            });

            // Show transaction details container
            transactionDetailsContainer.classList.remove('hidden');
        })
        .catch(error => console.error('Error fetching user transactions:', error));
}

function approveTransaction(transactionId) {
    fetch(`/admin/transactions/approve?transaction_id=${transactionId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ transaction_id: transactionId }) // Send transaction_id in JSON format
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            alert('Transaction approved successfully!');
            // Optionally, update UI or perform other actions upon approval
        })
        .catch(error => {
            console.error('Error approving transaction:', error);
            alert('An error occurred while approving the transaction. Please try again later.');
        });
}

document.addEventListener('DOMContentLoaded', function() {
    fetchUnassignedUsers();
});

document.addEventListener('DOMContentLoaded', function() {
    fetchUnassignedUsers();
});

document.addEventListener('DOMContentLoaded', function() {
    fetchUnassignedUsers();
});

function fetchUnassignedUsers() {
    fetch('/unassigned_users')
        .then(response => response.json())
        .then(data => {
            const unassignedUsersContainer = document.getElementById('unassignedUsersContainer');
            unassignedUsersContainer.innerHTML = ''; // Clear previous content

            if (data.length === 0) {
                unassignedUsersContainer.innerHTML = '<p>Tous les utilisateurs sont assignés à des administrateurs.</p>';
            } else {
                const userListElement = document.createElement('ul');
                userListElement.classList.add('unassigned-user-items');
                unassignedUsersContainer.innerHTML = '<h2>Voici les utilisateurs non assignés à un administrateur</h2>';
                data.forEach(user => {
                    const userItemElement = document.createElement('li');
                    userItemElement.classList.add('unassigned-user-item');

                    const usernameElement = document.createElement('p');
                    usernameElement.classList.add('user-username'); // Adding class to username element
                    usernameElement.textContent = `Utilisateur: ${user.username}`;

                    const emailElement = document.createElement('p');
                    emailElement.classList.add('user-email'); // Adding class to email element
                    emailElement.textContent = `Email: ${user.email}`;

                    userItemElement.appendChild(usernameElement);
                    userItemElement.appendChild(emailElement);

                    userListElement.appendChild(userItemElement);
                });

                unassignedUsersContainer.appendChild(userListElement);
            }
        })
        .catch(error => {
            console.error('Error fetching unassigned users:', error);
        });
}


// Function to toggle notification dropdown visibility
function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    dropdown.classList.toggle('hidden');
}

// Function to add a new notification
function addNotification(message) {
    const notificationList = document.getElementById('notificationList');
    const newNotification = document.createElement('li');
    newNotification.textContent = message;
    notificationList.appendChild(newNotification);

    // Update notification count
    const notificationCount = document.getElementById('notificationCount');
    notificationCount.textContent = parseInt(notificationCount.textContent) + 1;
    notificationCount.classList.remove('hidden');
}

// Simulated example: Adding a notification after a delay
setTimeout(() => {
    addNotification('Nouveau utilisateur ajouté');
}, 3000);  // Simulating after 3 seconds
