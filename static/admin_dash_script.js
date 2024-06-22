// Updated JavaScript code including Toastr notifications

let currentUserId = null;

function fetchUserTransactions(userId, filter = 'all') {
    currentUserId = userId;
    fetch(`/user_transactions/${userId}`)
        .then(response => response.json())
        .then(data => {
            const transactionDetailsContainer = document.getElementById('transactionDetailsContainer');
            const transactionDetails = document.getElementById('transactionDetails');
            transactionDetails.innerHTML = ''; // Clear previous details

            if (data.transactions.length === 0) {
                transactionDetails.innerHTML = '<p>Aucune transaction trouvée.</p>';
            } else {
                const filteredTransactions = data.transactions.filter(transaction => {
                    if (filter === 'all') return true;
                    if (filter === 'pending' && transaction.status === 'pending') return true;
                    if (filter === 'approved' && transaction.status !== 'pending' && transaction.status !== 'rejected') return true;
                    if (filter === 'rejected' && transaction.status === 'rejected') return true;
                    return false;
                });

                if (filteredTransactions.length === 0) {
                    transactionDetails.innerHTML = '<p>Aucune transaction trouvée pour ce filtre.</p>';
                    return;
                }

                const table = document.createElement('table');
                table.classList.add('azure-table', 'table', 'table-striped', 'table-bordered');

                const thead = document.createElement('thead');
                thead.innerHTML = `
                    <tr>
                        <th>Identifiant de transaction</th>
                        <th>Identifiant de l'expéditeur</th>
                        <th>Identifiant du destinataire</th>
                        <th>Montant</th>
                        <th>Type de transaction</th>
                        <th>Statut</th>
                        <th>Date de transaction</th>
                        <th>Actions</th>
                    </tr>
                `;
                table.appendChild(thead);

                const tbody = document.createElement('tbody');
                filteredTransactions.forEach(transaction => {
                    const transactionDate = new Date(transaction.transaction_date);
                    let statusClass = '';
                    let statusText = '';

                    if (transaction.status === 'pending') {
                        statusClass = 'status-pending'; 
                        statusText = 'En attente';
                    } else if (transaction.status === 'rejected') {
                        statusClass = 'status-rejected';
                        statusText = 'Rejeté';
                    } else {
                        // Assuming status is a date string for approved transactions
                        statusClass = 'status-confirmed'; 
                        const approvedDate = new Date(transaction.status);
                        statusText = approvedDate.toLocaleString('fr-FR', {
                            day: 'numeric',
                            month: 'numeric',
                            year: 'numeric',
                            hour: 'numeric',
                            minute: 'numeric',
                        });
                    }

                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${transaction.transaction_id}</td>
                        <td>${transaction.sender_id}</td>
                        <td>${transaction.recipient_id}</td>
                        <td>${transaction.amount}</td>
                        <td>${transaction.transaction_type}</td>
                        <td><span class="${statusClass}">${statusText}</span></td>
                        <td>${transactionDate.toLocaleString()}</td>
                        <td class="action-buttons">
                        ${transaction.status === 'pending' ? `
                            <div class="button-group">
                                <button class="button_app" onclick="approveTransaction('${transaction.transaction_id}')">Approuver</button>
                                <button class="button_rej" onclick="rejectTransaction('${transaction.transaction_id}')">Rejeté</button>
                            </div>
                        ` : ''}
                    </td>
                    `;

                    tbody.appendChild(row);
                });

                table.appendChild(tbody);
                transactionDetails.appendChild(table);
            }

            transactionDetailsContainer.classList.remove('hidden');
        })
        .catch(error => console.error('Erreur lors du chargement des transactions utilisateur :', error));
}

function applyFilter() {
    const filter = document.getElementById('transactionFilter').value;
    fetchUserTransactions(currentUserId, filter);
}

function approveTransaction(transactionId) {
    fetch(`/admin/transactions/approve?transaction_id=${transactionId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ transaction_id: transactionId })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('La réponse du réseau n\'est pas satisfaisante');
            }
            return response.json();
        })
        .then(data => {
            toastr.success('Transaction approuvée avec succès !');
            fetchUserTransactions(data.user_id); // Refresh transaction details
        })
        .catch(error => {
            console.error('Erreur lors de l\'approbation de la transaction :', error);
            toastr.error('Une erreur est survenue lors de l\'approbation de la transaction. Veuillez réessayer plus tard.');
        });
}

function rejectTransaction(transactionId) {
    fetch(`/admin/transactions/reject?transaction_id=${transactionId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ transaction_id: transactionId })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('La réponse du réseau n\'est pas satisfaisante');
            }
            return response.json();
        })
        .then(data => {
            toastr.success('Transaction rejetée avec succès !');
            fetchUserTransactions(data.user_id); // Refresh transaction details
        })
        .catch(error => {
            console.error('Erreur lors du rejet de la transaction :', error);
            toastr.error('Une erreur est survenue lors du rejet de la transaction. Veuillez réessayer plus tard.');
        });
}

toastr.options = {
    "closeButton": true,
    "debug": false,
    "newestOnTop": true,
    "progressBar": true,
    "positionClass": "toast-top-right",
    "preventDuplicates": true,
    "onclick": null,
    "showDuration": "300",
    "hideDuration": "1000",
    "timeOut": "5000",
    "extendedTimeOut": "1000",
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "fadeIn",
    "hideMethod": "fadeOut"
};

// Initial fetch of user transactions upon page load
fetchUserTransactions(currentUserId);
