// Interactive Legal Case File Manager JavaScript

class InteractiveSearch {
    constructor() {
        try {
            this.searchInput = document.getElementById('q');
            this.searchForm = document.getElementById('search-form');
            this.resultsContainer = document.getElementById('results-container');
            this.resultsBody = document.getElementById('results-body');
            this.resultsCount = document.getElementById('results-count');
            this.searchStatus = document.getElementById('search-status');
            this.searchIcon = document.getElementById('search-icon');
            this.searchSpinner = document.getElementById('search-spinner');
            this.suggestionsContainer = document.getElementById('search-suggestions');
            this.clearButton = document.getElementById('clear-search');
            
            console.log('InteractiveSearch elements:', {
                searchInput: !!this.searchInput,
                suggestionsContainer: !!this.suggestionsContainer,
                searchForm: !!this.searchForm
            });
            
            this.searchTimeout = null;
            this.suggestionTimeout = null;
            this.currentRequest = null;
            this.isSearching = false;
            
            if (this.searchInput && this.suggestionsContainer) {
                this.init();
            } else {
                console.error('InteractiveSearch: Required elements not found');
            }
        } catch (error) {
            console.error('InteractiveSearch constructor error:', error);
        }
    }
    
    init() {
        this.bindEvents();
        
        // Trigger initial search if there are existing params
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');
        if (query || this.hasActiveFilters()) {
            this.performSearch();
        }
    }
    
    bindEvents() {
        // Real-time search as you type
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });
        
        // Handle suggestions
        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.length >= 2) {
                this.showSuggestions(this.searchInput.value);
            }
        });
        
        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            // Don't interfere with file detail links
            if (e.target.closest('.file-detail-link')) {
                return;
            }
            if (!this.searchInput.contains(e.target) && !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
        
        // Handle filter changes
        document.querySelectorAll('.interactive-filter').forEach(filter => {
            filter.addEventListener('change', () => {
                this.handleFilterChange();
            });
        });
        
        // Clear search button
        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => {
                this.clearSearch();
            });
        }
        
        // Prevent form submission
        this.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
        });
        
        // Keyboard navigation for suggestions
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
    }
    
    handleSearchInput(query) {
        clearTimeout(this.searchTimeout);
        
        if (query.length >= 2) {
            // Show suggestions
            clearTimeout(this.suggestionTimeout);
            this.suggestionTimeout = setTimeout(() => {
                this.showSuggestions(query);
            }, 200);
            
            // Perform search
            this.searchTimeout = setTimeout(() => {
                this.performSearch();
            }, 500);
            
            this.updateSearchStatus('Searching...');
        } else if (query.length === 0) {
            this.hideSuggestions();
            if (this.hasActiveFilters()) {
                this.performSearch();
            } else {
                this.showWelcomeMessage();
                this.updateSearchStatus('Start typing to search...');
            }
        } else {
            this.hideSuggestions();
            this.updateSearchStatus('Type at least 2 characters...');
        }
    }
    
    hasActiveFilters() {
        const filters = document.querySelectorAll('.interactive-filter');
        return Array.from(filters).some(filter => filter.value);
    }
    
    getActiveFilters() {
        const filters = {};
        document.querySelectorAll('.interactive-filter').forEach(filter => {
            if (filter.value) {
                filters[filter.name] = filter.value;
            }
        });
        return filters;
    }
    
    handleKeyNavigation(e) {
        const suggestions = this.suggestionsContainer.querySelectorAll('.suggestion-item');
        if (suggestions.length === 0) return;
        
        const activeIndex = Array.from(suggestions).findIndex(s => s.classList.contains('active'));
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = activeIndex < suggestions.length - 1 ? activeIndex + 1 : 0;
                this.setActiveSuggestion(suggestions, nextIndex);
                break;
            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = activeIndex > 0 ? activeIndex - 1 : suggestions.length - 1;
                this.setActiveSuggestion(suggestions, prevIndex);
                break;
            case 'Enter':
                e.preventDefault();
                if (activeIndex >= 0) {
                    suggestions[activeIndex].click();
                } else {
                this.performSearch();
                }
                break;
            case 'Escape':
                this.hideSuggestions();
                break;
        }
    }
    
    setActiveSuggestion(suggestions, index) {
        suggestions.forEach(s => s.classList.remove('active'));
        suggestions[index].classList.add('active');
        this.searchInput.value = suggestions[index].textContent;
    }
    
    handleFilterChange() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch();
        }, 300);
    }
    
    async performSearch() {
        if (this.isSearching) {
            if (this.currentRequest) {
                this.currentRequest.abort();
            }
        }
        
        this.isSearching = true;
        this.showLoadingState();
        
        const query = this.searchInput.value.trim();
        const filters = this.getActiveFilters();
        
        // Build query parameters
        const params = new URLSearchParams();
        if (query) params.set('q', query);
        Object.entries(filters).forEach(([key, value]) => {
            if (value) params.set(key, value);
        });
        
        try {
            const controller = new AbortController();
            this.currentRequest = controller;
            
            const response = await fetch(`/api/unified-search?${params}`, {
                signal: controller.signal
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.renderUnifiedResults(data);
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Search error:', error);
                this.showErrorState();
            }
        } finally {
            this.isSearching = false;
            this.hideLoadingState();
            this.currentRequest = null;
        }
    }
    
    renderUnifiedResults(data) {
        const { files, clients, cases, payments, access_history, comments, total_results, query, category_counts } = data;
        
        // Update search status
        const searchStatus = document.getElementById('search-status');
        const resultsCount = document.getElementById('results-count');
        const resultsBody = document.getElementById('results-body');
        
        if (total_results === 0) {
            searchStatus.textContent = query ? `No results for "${query}"` : 'Start typing to search...';
            resultsCount.textContent = '0 results';
            
            resultsBody.innerHTML = `
                <div class="text-center py-5" id="no-results">
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">No results found</h5>
                    <p class="text-muted">Try adjusting your search criteria or using different keywords.</p>
                </div>
            `;
        } else {
            searchStatus.textContent = query ? `Found results for "${query}"` : 'Search results';
            resultsCount.textContent = `${total_results} result${total_results !== 1 ? 's' : ''}`;
            
            let html = '';
            
            // Add category summary
            if (total_results > 0) {
                html += this.renderCategorySummary(category_counts);
            }
            
            // Render each category
            if (files && files.length > 0) {
                html += this.renderFileResults(files, data.files_truncated);
            }
            if (clients && clients.length > 0) {
                html += this.renderClientResults(clients, data.clients_truncated);
            }
            if (cases && cases.length > 0) {
                html += this.renderCaseResults(cases, data.cases_truncated);
            }
            if (payments && payments.length > 0) {
                html += this.renderPaymentResults(payments, data.payments_truncated);
            }
            if (access_history && access_history.length > 0) {
                html += this.renderAccessHistoryResults(access_history, data.access_history_truncated);
            }
            if (comments && comments.length > 0) {
                html += this.renderCommentResults(comments, data.comments_truncated);
            }
            
            resultsBody.innerHTML = html || '<div class="text-center py-5"><p class="text-muted">No results found</p></div>';
        }
    }
    
    renderCategorySummary(categoryCounts) {
        const categories = [
            { key: 'files', label: 'Files', icon: 'file-alt', color: 'primary' },
            { key: 'clients', label: 'Clients', icon: 'users', color: 'success' },
            { key: 'cases', label: 'Cases', icon: 'briefcase', color: 'info' },
            { key: 'payments', label: 'Payments', icon: 'dollar-sign', color: 'warning' },
            { key: 'access_history', label: 'Access History', icon: 'history', color: 'secondary' },
            { key: 'comments', label: 'Comments', icon: 'comments', color: 'dark' }
        ];
        
        let html = `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title mb-3">
                                <i class="fas fa-chart-pie me-2"></i>Search Results Summary
                            </h6>
                            <div class="row">
        `;
        
        categories.forEach(category => {
            const count = categoryCounts[category.key] || 0;
            if (count > 0) {
                html += `
                    <div class="col-md-2 col-sm-4 col-6 mb-2">
                        <div class="d-flex align-items-center">
                            <span class="badge bg-${category.color} me-2">
                                <i class="fas fa-${category.icon}"></i>
                            </span>
                            <div>
                                <small class="text-muted">${category.label}</small><br>
                                <strong>${count}</strong>
                            </div>
                        </div>
                    </div>
                `;
            }
        });
        
        html += `
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderFileResults(files, truncated) {
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-file-alt me-2 text-primary"></i>
                        Files (${files.length}${truncated ? '+' : ''})
                        ${truncated ? '<small class="text-muted ms-2">Showing top results</small>' : ''}
                    </h5>
                </div>
                <div class="card-body">
            <div class="table-responsive">
                        <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Reference #</th>
                            <th>Client</th>
                            <th>Case Type</th>
                            <th>File Type</th>
                            <th>Location</th>
                                    <th>Relevance</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        files.forEach(file => {
            html += `
                <tr class="result-row">
                    <td>
                        <strong class="text-primary">${file.reference_number}</strong><br>
                        <small class="text-muted">${file.file_id}</small>
                        ${file.match_details ? `<br><small class="text-info">${file.match_details.slice(0,2).join(', ')}</small>` : ''}
                </td>
                <td>
                        <a href="/client/${file.client_id}" class="text-decoration-none">
                            ${file.client_name}
                    </a>
                </td>
                <td>
                        <span class="badge bg-info">${file.case_type}</span>
                </td>
                    <td>${file.file_type}</td>
                <td>
                        <strong>${file.warehouse_location}</strong><br>
                        <small class="text-muted">${file.shelf_number} - ${file.box_number}</small>
                </td>
                <td>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar" role="progressbar" style="width: ${Math.min(100, (file.relevance_score || 0) * 10)}%">
                                ${file.relevance_score || 0}
                            </div>
                        </div>
                </td>
                <td>
                        <a href="/file/${file.file_id}" class="btn btn-sm btn-outline-primary file-detail-link">
                        <i class="fas fa-eye me-1"></i>Details
                    </a>
                </td>
            </tr>
        `;
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderClientResults(clients, truncated) {
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-users me-2 text-success"></i>
                        Clients (${clients.length}${truncated ? '+' : ''})
                        ${truncated ? '<small class="text-muted ms-2">Showing top results</small>' : ''}
                    </h5>
                        </div>
                <div class="card-body">
                    <div class="row">
        `;
        
        clients.forEach(client => {
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title">
                                <a href="/client/${client.client_id}" class="text-decoration-none">
                                    ${client.first_name} ${client.last_name}
                                </a>
                            </h6>
                            <p class="card-text">
                                <small class="text-muted">
                                    <i class="fas fa-envelope me-1"></i>${client.email}<br>
                                    <i class="fas fa-phone me-1"></i>${client.phone}<br>
                                    <i class="fas fa-tag me-1"></i>${client.client_type}
                                </small>
                            </p>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="badge bg-${client.status === 'Active' ? 'success' : client.status === 'Inactive' ? 'secondary' : 'warning'}">
                                    ${client.status}
                                </span>
                                <small class="text-primary">Score: ${client.relevance_score}</small>
                    </div>
                            ${client.match_details ? `<small class="text-info mt-2 d-block">${client.match_details.slice(0,2).join(', ')}</small>` : ''}
                        </div>
                    </div>
                        </div>
            `;
        });
        
        html += `
                    </div>
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderCaseResults(cases, truncated) {
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-briefcase me-2 text-info"></i>
                        Cases (${cases.length}${truncated ? '+' : ''})
                        ${truncated ? '<small class="text-muted ms-2">Showing top results</small>' : ''}
                    </h5>
            </div>
                <div class="card-body">
        `;
        
        cases.forEach(case_item => {
            html += `
                <div class="card mb-3">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <h6 class="card-title">
                                    ${case_item.reference_number}
                                    <span class="badge bg-info ms-2">${case_item.case_type}</span>
                                </h6>
                                <p class="card-text">
                                    <strong>Client:</strong> 
                                    <a href="/client/${case_item.client_id}" class="text-decoration-none">
                                        ${case_item.client_name}
                                    </a><br>
                                    <strong>Lawyer:</strong> ${case_item.assigned_lawyer}<br>
                                    <small class="text-muted">${case_item.description.substring(0, 100)}...</small>
                                </p>
                                ${case_item.match_details ? `<small class="text-info">${case_item.match_details.slice(0,2).join(', ')}</small>` : ''}
                            </div>
                            <div class="col-md-4 text-end">
                                <div class="mb-2">
                                    <span class="badge bg-${case_item.case_status === 'Open' ? 'success' : case_item.case_status === 'Closed' ? 'secondary' : 'warning'}">
                                        ${case_item.case_status}
                                    </span>
                                    <span class="badge bg-${case_item.priority === 'High' ? 'danger' : case_item.priority === 'Medium' ? 'warning' : 'info'} ms-1">
                                        ${case_item.priority}
                                    </span>
                                </div>
                                <small class="text-muted">
                                    Value: $${case_item.estimated_value?.toLocaleString()}<br>
                                    Score: ${case_item.relevance_score}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderPaymentResults(payments, truncated) {
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-dollar-sign me-2 text-warning"></i>
                        Payments (${payments.length}${truncated ? '+' : ''})
                        ${truncated ? '<small class="text-muted ms-2">Showing top results</small>' : ''}
                    </h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Payment ID</th>
                                    <th>Client</th>
                                    <th>Amount</th>
                                    <th>Method</th>
                                    <th>Status</th>
                                    <th>Date</th>
                                    <th>Relevance</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        payments.forEach(payment => {
            html += `
                <tr>
                    <td>
                        <strong>${payment.payment_id}</strong>
                        ${payment.match_details ? `<br><small class="text-info">${payment.match_details.slice(0,2).join(', ')}</small>` : ''}
                    </td>
                    <td>
                        <a href="/client/${payment.client_id}" class="text-decoration-none">
                            ${payment.client_name}
                        </a>
                    </td>
                    <td><strong>$${payment.amount.toLocaleString()}</strong></td>
                    <td>${payment.payment_method}</td>
                    <td>
                        <span class="badge bg-${payment.status === 'Paid' ? 'success' : payment.status === 'Pending' ? 'warning' : 'danger'}">
                            ${payment.status}
                        </span>
                    </td>
                    <td><small class="text-muted">${payment.payment_date}</small></td>
                    <td><small class="text-primary">${payment.relevance_score}</small></td>
                </tr>
            `;
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderAccessHistoryResults(accessHistory, truncated) {
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-history me-2 text-secondary"></i>
                        Access History (${accessHistory.length}${truncated ? '+' : ''})
                        ${truncated ? '<small class="text-muted ms-2">Showing top results</small>' : ''}
                    </h5>
                </div>
                <div class="card-body">
        `;
        
        accessHistory.forEach(access => {
            html += `
                <div class="d-flex align-items-start mb-3 p-2 border rounded">
                    <div class="me-3">
                        <div class="bg-secondary rounded-circle d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                            <i class="fas fa-${access.access_type === 'view' ? 'eye' : access.access_type === 'search' ? 'search' : 'download'} text-white"></i>
                        </div>
                    </div>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <strong class="text-primary">${access.user_name}</strong>
                                <span class="badge bg-info ms-1">${access.user_role}</span>
                                <div class="text-muted mt-1">
                                    ${access.access_type.charAt(0).toUpperCase() + access.access_type.slice(1)}ed file 
                                    <a href="/file/${access.file_id}" class="text-decoration-none fw-bold">
                                        ${access.file_reference}
                                    </a>
                                </div>
                                <small class="text-muted">
                                    Client: ${access.client_name} | IP: ${access.ip_address}
                                </small>
                                ${access.match_details ? `<br><small class="text-info">${access.match_details.slice(0,2).join(', ')}</small>` : ''}
                            </div>
                            <div class="text-end">
                                <small class="text-muted">${new Date(access.access_timestamp).toLocaleDateString()}</small>
                                <br><small class="text-primary">Score: ${access.relevance_score}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderCommentResults(comments, truncated) {
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-comments me-2 text-dark"></i>
                        Comments (${comments.length}${truncated ? '+' : ''})
                        ${truncated ? '<small class="text-muted ms-2">Showing top results</small>' : ''}
                    </h5>
                </div>
                <div class="card-body">
        `;
        
        comments.forEach(comment => {
            html += `
                <div class="card mb-3">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <strong class="text-primary">${comment.user_name}</strong>
                                <span class="badge bg-secondary ms-1">${comment.user_role}</span>
                                ${comment.is_private ? '<span class="badge bg-warning ms-1">Private</span>' : ''}
                            </div>
                            <div class="text-end">
                                <small class="text-muted">${new Date(comment.created_timestamp).toLocaleDateString()}</small>
                                <br><small class="text-primary">Score: ${comment.relevance_score}</small>
                            </div>
                        </div>
                        <p class="card-text">${comment.comment_text}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                <i class="fas fa-tag me-1"></i>${comment.entity_type}
                                ${comment.entity_info ? ` - ${comment.entity_info}` : ''}
                            </small>
                        </div>
                        ${comment.match_details ? `<small class="text-info mt-2 d-block">${comment.match_details.slice(0,2).join(', ')}</small>` : ''}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }

    async showSuggestions(query) {
        console.log('showSuggestions called with:', query, 'Container exists:', !!this.suggestionsContainer);
        
        if (query.length < 1) {
            this.hideSuggestions();
            return;
        }
        
        try {
            const url = `/api/intelligent-suggestions?q=${encodeURIComponent(query)}&limit=12&categories=true`;
            console.log('Fetching suggestions from:', url);
            
            const response = await fetch(url);
            const data = await response.json();
            
            console.log('Suggestions response:', data);
            
            if (data.suggestions && data.suggestions.length > 0) {
                let html = this.renderIntelligentSuggestions(data);
                
                console.log('Setting suggestions HTML, container:', this.suggestionsContainer);
                this.suggestionsContainer.innerHTML = html;
                this.suggestionsContainer.classList.remove('d-none');
                console.log('Suggestions container classes after show:', this.suggestionsContainer.className);
                
                // Add click handlers
                this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const text = item.getAttribute('data-text');
                        this.searchInput.value = text;
                        this.hideSuggestions();
                        this.performSearch();
                    });
                });
            } else if (query.length >= 2) {
                // Show "no suggestions" message for longer queries
                this.suggestionsContainer.innerHTML = `
                    <div class="px-3 py-2 text-muted text-center">
                        <i class="fas fa-search me-2"></i>No suggestions found
                    </div>
                `;
                this.suggestionsContainer.classList.remove('d-none');
                console.log('No suggestions message shown');
            } else {
                this.hideSuggestions();
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
            this.hideSuggestions();
        }
    }
    
    renderIntelligentSuggestions(data) {
        let html = '';
        const { suggestions, recent_searches, popular_searches } = data;
        
        // Group suggestions by type for better display
        const grouped = {
            contextual: [],
            clients: [],
            recent: [],
            completions: [],
            corrections: [],
            cases: [],
            files: [],
            payments: [],
            popular: []
        };
        
        suggestions.forEach(suggestion => {
            const type = suggestion.type;
            const category = type.includes('client') ? 'clients' : 
                           type.includes('case') ? 'cases' :
                           type.includes('file') || type.includes('keyword') || type.includes('document') ? 'files' :
                           type.includes('payment') ? 'payments' :
                           type.includes('recent') ? 'recent' :
                           type.includes('popular') ? 'popular' :
                           type.includes('completion') ? 'completions' :
                           type.includes('correction') ? 'corrections' :
                           'contextual';
            grouped[category].push(suggestion);
        });
        
        // Show suggestions by priority
        const sections = [
            { key: 'contextual', label: 'Suggested', icon: 'lightbulb', color: 'warning' },
            { key: 'recent', label: 'Recent', icon: 'history', color: 'info' },
            { key: 'completions', label: 'Complete', icon: 'magic', color: 'primary' },
            { key: 'corrections', label: 'Did you mean?', icon: 'spell-check', color: 'danger' },
            { key: 'clients', label: 'Clients', icon: 'user', color: 'success' },
            { key: 'cases', label: 'Cases', icon: 'briefcase', color: 'info' },
            { key: 'files', label: 'Files', icon: 'file', color: 'primary' },
            { key: 'payments', label: 'Payments', icon: 'dollar-sign', color: 'warning' },
            { key: 'popular', label: 'Popular', icon: 'star', color: 'secondary' }
        ];
        
        let hasAnyResults = false;
        
        sections.forEach(section => {
            const items = grouped[section.key];
            if (items && items.length > 0) {
                if (hasAnyResults) {
                    html += `<div class="border-top my-1"></div>`;
                }
                
                // Section header (only show for multiple sections)
                if (Object.values(grouped).filter(g => g.length > 0).length > 1) {
                    html += `
                        <div class="px-3 py-1 bg-light text-muted small">
                            <i class="fas fa-${section.icon} me-2 text-${section.color}"></i>
                            ${section.label}
                        </div>
                    `;
                }
                
                items.slice(0, 4).forEach(item => { // Limit per section
                    html += this.renderSuggestionItem(item);
                });
                
                hasAnyResults = true;
            }
        });
        
        // If no suggestions but we have recent or popular searches, show them
        if (!hasAnyResults && (recent_searches.length > 0 || popular_searches.length > 0)) {
            if (recent_searches.length > 0) {
                html += `
                    <div class="px-3 py-1 bg-light text-muted small">
                        <i class="fas fa-history me-2 text-info"></i>Recent Searches
                    </div>
                `;
                recent_searches.slice(0, 3).forEach(search => {
                    html += `
                        <div class="suggestion-item px-3 py-2 border-bottom cursor-pointer d-flex align-items-center" data-text="${search}">
                            <i class="fas fa-history me-3 text-info"></i>
                            <span>${search}</span>
                        </div>
                    `;
                });
            }
            
            if (popular_searches.length > 0) {
                html += `
                    <div class="px-3 py-1 bg-light text-muted small">
                        <i class="fas fa-star me-2 text-warning"></i>Popular Searches
                    </div>
                `;
                popular_searches.slice(0, 2).forEach(([search, count]) => {
                    html += `
                        <div class="suggestion-item px-3 py-2 border-bottom cursor-pointer d-flex align-items-center justify-content-between" data-text="${search}">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-star me-3 text-warning"></i>
                                <span>${search}</span>
                            </div>
                            <small class="text-muted">${count}</small>
                        </div>
                    `;
                });
            }
        }
        
        return html;
    }
    
    renderSuggestionItem(suggestion) {
        const icons = {
            'contextual': 'lightbulb',
            'client': 'user',
            'case_reference': 'briefcase',
            'case_type': 'briefcase',
            'file_reference': 'file-alt',
            'file_type': 'file',
            'keyword': 'tag',
            'document_category': 'folder',
            'payment_amount': 'dollar-sign',
            'payment_method': 'credit-card',
            'recent_search': 'history',
            'popular_search': 'star',
            'name_completion': 'user-check',
            'case_type_completion': 'briefcase',
            'file_type_completion': 'file-check',
            'typo_correction': 'spell-check'
        };
        
        const colors = {
            'contextual': 'warning',
            'client': 'success',
            'case_reference': 'info',
            'case_type': 'info',
            'file_reference': 'primary',
            'file_type': 'primary',
            'keyword': 'secondary',
            'document_category': 'secondary',
            'payment_amount': 'warning',
            'payment_method': 'warning',
            'recent_search': 'info',
            'popular_search': 'secondary',
            'name_completion': 'success',
            'case_type_completion': 'info',
            'file_type_completion': 'primary',
            'typo_correction': 'danger'
        };
        
        const icon = icons[suggestion.type] || 'search';
        const color = colors[suggestion.type] || 'muted';
        
        let subtitle = '';
        if (suggestion.email) {
            subtitle = `<small class="text-muted d-block">${suggestion.email}</small>`;
        } else if (suggestion.case_type && suggestion.type === 'case_reference') {
            subtitle = `<small class="text-muted d-block">${suggestion.case_type}</small>`;
        } else if (suggestion.client && suggestion.type === 'file_reference') {
            subtitle = `<small class="text-muted d-block">Client: ${suggestion.client}</small>`;
        } else if (suggestion.context) {
            subtitle = `<small class="text-muted d-block">${suggestion.context.replace('_', ' ')}</small>`;
        } else if (suggestion.original && suggestion.type === 'typo_correction') {
            subtitle = `<small class="text-muted d-block">Instead of "${suggestion.original}"</small>`;
        }
        
        return `
            <div class="suggestion-item px-3 py-2 border-bottom cursor-pointer d-flex align-items-center" data-text="${suggestion.text}">
                <i class="fas fa-${icon} me-3 text-${color}"></i>
                <div class="flex-grow-1">
                    <div>${suggestion.text}</div>
                    ${subtitle}
                </div>
                ${suggestion.count ? `<small class="text-muted ms-2">${suggestion.count}</small>` : ''}
            </div>
        `;
    }
    
    hideSuggestions() {
        this.suggestionsContainer.classList.add('d-none');
        this.suggestionsContainer.innerHTML = '';
    }
    
    clearSearch() {
        this.searchInput.value = '';
        document.querySelectorAll('.interactive-filter').forEach(filter => {
            filter.value = '';
        });
        this.hideSuggestions();
        this.showWelcomeMessage();
        this.updateSearchStatus('Start typing to search...');
    }
    
    showWelcomeMessage() {
        this.resultsBody.innerHTML = `
            <div class="text-center py-5" id="welcome-message">
                <i class="fas fa-search fa-3x text-primary mb-3"></i>
                <h5 class="text-primary">Unified Search</h5>
                <p class="text-muted">Search across files, clients, cases, payments, access history, and comments.</p>
                <div class="row mt-4">
                    <div class="col-md-4">
                        <div class="p-3 bg-light rounded">
                            <i class="fas fa-keyboard fa-2x text-info mb-2"></i>
                            <h6>Real-time Search</h6>
                            <small class="text-muted">Results appear as you type</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 bg-light rounded">
                            <i class="fas fa-filter fa-2x text-success mb-2"></i>
                            <h6>Smart Filters</h6>
                            <small class="text-muted">Combine filters instantly</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 bg-light rounded">
                            <i class="fas fa-lightbulb fa-2x text-warning mb-2"></i>
                            <h6>Auto-suggestions</h6>
                            <small class="text-muted">Get suggestions as you type</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    showLoadingState() {
        this.searchIcon.classList.add('d-none');
        this.searchSpinner.classList.remove('d-none');
    }
    
    hideLoadingState() {
        this.searchIcon.classList.remove('d-none');
        this.searchSpinner.classList.add('d-none');
    }
    
    showErrorState() {
        this.resultsBody.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                <h5 class="text-warning">Search Error</h5>
                <p class="text-muted">There was an error performing your search. Please try again.</p>
            </div>
        `;
    }
    
    updateSearchStatus(message) {
        if (this.searchStatus) {
            this.searchStatus.textContent = message;
        }
    }
}

// Dashboard Search functionality
class DashboardSearch {
    constructor() {
        try {
            this.searchInput = document.getElementById('dashboard-search');
            this.suggestionsContainer = document.getElementById('dashboard-suggestions');
            this.searchForm = document.getElementById('dashboard-search-form');
            
            console.log('DashboardSearch elements:', {
                searchInput: !!this.searchInput,
                suggestionsContainer: !!this.suggestionsContainer,
                searchForm: !!this.searchForm
            });
            
            this.suggestionTimeout = null;
            
            if (this.searchInput && this.suggestionsContainer) {
                this.init();
            } else {
                console.error('DashboardSearch: Required elements not found');
            }
        } catch (error) {
            console.error('DashboardSearch constructor error:', error);
        }
    }
    
    init() {
        if (!this.searchInput) return;
        
        this.bindEvents();
        
        // Add single event delegation handler for all suggestion clicks
        this.suggestionsContainer.addEventListener('click', (e) => {
            console.log('🔍 Dashboard suggestions container clicked:', {
                target: e.target.tagName + '.' + e.target.className,
                clientX: e.clientX,
                clientY: e.clientY
            });
            
            const suggestionItem = e.target.closest('.dashboard-suggestion-item');
            if (suggestionItem) {
                e.preventDefault();
                e.stopPropagation();
                
                const text = suggestionItem.getAttribute('data-text');
                const type = suggestionItem.getAttribute('data-type');
                const url = suggestionItem.getAttribute('data-url');
                
                // Find which item number this is
                const allItems = this.suggestionsContainer.querySelectorAll('.dashboard-suggestion-item');
                const itemIndex = Array.from(allItems).indexOf(suggestionItem) + 1;
                
                console.log(`✅ Dashboard suggestion ${itemIndex} clicked:`, {
                    text: text,
                    type: type, 
                    url: url,
                    element: suggestionItem.tagName
                });
                
                if (!text) {
                    console.error('No data-text found on suggestion item');
                    return;
                }
                
                this.handleSuggestionClick(text, type, url);
            } else {
                console.warn('❌ Click did not find .dashboard-suggestion-item ancestor');
                console.log('Clicked element:', e.target);
                console.log('Available suggestion items:', this.suggestionsContainer.querySelectorAll('.dashboard-suggestion-item').length);
            }
        });
    }
    
    handleSuggestionClick(text, type, url) {
        /**
         * Centralized handler for all suggestion clicks
         * Implements smart routing based on suggestion type
         */
        try {
            let targetUrl;
            
            // Smart routing based on suggestion type
            if (type === 'client' && url) {
                // Direct navigation to client page for client suggestions
                targetUrl = url;
                console.log('Navigating to client page:', targetUrl);
            } else if (type === 'file' && url) {
                // Direct navigation to file page for file suggestions  
                targetUrl = url;
                console.log('Navigating to file page:', targetUrl);
            } else {
                // Fallback to search for other types
                targetUrl = `/search?q=${encodeURIComponent(text)}`;
                console.log('Navigating to search:', targetUrl);
            }
            
            // Validate URL before navigation
            if (!targetUrl) {
                console.error('No target URL determined for suggestion:', { text, type, url });
                return;
            }
            
            // Hide suggestions and navigate
            this.hideSuggestions();
            console.log('Final navigation to:', targetUrl);
            window.location.href = targetUrl;
            
        } catch (error) {
            console.error('Error handling suggestion click:', error, { text, type, url });
            // Fallback to search if there's an error
            const fallbackUrl = `/search?q=${encodeURIComponent(text)}`;
            console.log('Fallback navigation to:', fallbackUrl);
            this.hideSuggestions();
            window.location.href = fallbackUrl;
        }
    }
    
    bindEvents() {
        this.searchInput.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });
        
        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.length >= 2) {
                this.showSuggestions(this.searchInput.value);
            }
        });
        
        document.addEventListener('click', (e) => {
            // Don't interfere with file detail links
            if (e.target.closest('.file-detail-link')) {
                return;
            }
            if (!this.searchInput.contains(e.target) && !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
        
        this.searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
            const query = this.searchInput.value.trim();
            if (query) {
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
        });
    }
    
    handleInput(value) {
        clearTimeout(this.suggestionTimeout);
        
        if (value.length >= 2) {
            this.suggestionTimeout = setTimeout(() => {
                this.showSuggestions(value);
            }, 300);
        } else {
            this.hideSuggestions();
        }
    }
    
    async showSuggestions(query) {
        console.log('DashboardSearch showSuggestions called with:', query);
        
        try {
            const url = `/api/intelligent-suggestions?q=${encodeURIComponent(query)}&limit=8&categories=true`;
            console.log('Fetching dashboard suggestions from:', url);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Dashboard suggestions response:', data);
            
            if (!data) {
                console.warn('No data received from suggestions API');
                this.hideSuggestions();
                return;
            }
            
            if (data.suggestions && data.suggestions.length > 0) {
                let html = '';
                console.log('Processing', data.suggestions.length, 'suggestions');
                
                data.suggestions.slice(0, 6).forEach((suggestion, index) => {
                    // Validate suggestion data
                    if (!suggestion.text) {
                        console.warn(`Suggestion ${index + 1} missing text:`, suggestion);
                        return;
                    }
                    
                    console.log(`Suggestion ${index + 1}:`, {
                        text: suggestion.text,
                        type: suggestion.type,
                        url: suggestion.url
                    });
                    const icons = {
                        'contextual': 'lightbulb',
                        'client': 'user',
                        'file': 'file-alt',  // Added missing 'file' type
                        'case_reference': 'briefcase',
                        'case_type': 'briefcase', 
                        'file_reference': 'file-alt',
                        'file_type': 'file',
                        'keyword': 'tag',
                        'recent_search': 'history',
                        'popular_search': 'star'
                    };
                    
                    const colors = {
                        'contextual': 'warning',
                        'client': 'success',
                        'file': 'primary',  // Added missing 'file' type
                        'case_reference': 'info',
                        'case_type': 'info',
                        'file_reference': 'primary',
                        'file_type': 'primary', 
                        'keyword': 'secondary',
                        'recent_search': 'info',
                        'popular_search': 'warning'
                    };
                    
                    const icon = icons[suggestion.type] || 'search';
                    const color = colors[suggestion.type] || 'primary';
                    
                    html += `
                        <div class="dashboard-suggestion-item px-3 py-2 border-bottom cursor-pointer d-flex align-items-center" 
                             data-text="${suggestion.text}" 
                             data-type="${suggestion.type || 'search'}"
                             data-url="${suggestion.url || ''}"
                             style="cursor: pointer; user-select: none;"
                             onmouseover="this.style.backgroundColor='#f8f9fa'" 
                             onmouseout="this.style.backgroundColor='transparent'">
                            <i class="fas fa-${icon} me-2 text-${color}"></i>
                            <span>${suggestion.text}</span>
                            ${suggestion.email ? `<small class="text-muted ms-auto">${suggestion.email}</small>` : ''}
                        </div>
                    `;
                });
                
                this.suggestionsContainer.innerHTML = html;
                this.suggestionsContainer.classList.remove('d-none');
                
                // Verify DOM update completed
                const renderedItems = this.suggestionsContainer.querySelectorAll('.dashboard-suggestion-item');
                console.log('DOM updated with', renderedItems.length, 'suggestion items');
                
                // Verify each item has required data attributes and test clickability
                renderedItems.forEach((item, index) => {
                    const text = item.getAttribute('data-text');
                    const type = item.getAttribute('data-type');
                    const url = item.getAttribute('data-url');
                    
                    if (!text) {
                        console.error(`Item ${index + 1} missing data-text attribute`);
                    }
                    if (!type) {
                        console.warn(`Item ${index + 1} missing data-type attribute`);
                    }
                    
                    // Test if element is properly positioned and clickable
                    const rect = item.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0;
                    const hasClass = item.classList.contains('dashboard-suggestion-item');
                    const hasPointer = window.getComputedStyle(item).cursor === 'pointer';
                    
                    console.log(`Item ${index + 1} ready:`, { 
                        text, 
                        type, 
                        url,
                        visible: isVisible,
                        hasClass: hasClass,
                        cursor: hasPointer,
                        bounds: `${rect.width}x${rect.height}`,
                        top: rect.top
                    });
                    
                    // Add a test click listener to each item for debugging
                    item.addEventListener('click', function(e) {
                        console.log(`🔍 DIRECT CLICK on item ${index + 1}:`, text);
                    }, { once: true });
                });
                
                console.log('Event delegation active for all suggestion items');
            } else if (data.recent_searches && data.recent_searches.length > 0) {
                // Show recent searches if no suggestions
                let html = `
                    <div class="px-3 py-1 bg-light text-muted small">
                        <i class="fas fa-history me-2"></i>Recent Searches
                    </div>
                `;
                data.recent_searches.slice(0, 3).forEach(search => {
                    html += `
                        <div class="dashboard-suggestion-item px-3 py-2 border-bottom cursor-pointer" 
                             data-text="${search}"
                             data-type="recent_search"
                             data-url=""
                             style="cursor: pointer; user-select: none;"
                             onmouseover="this.style.backgroundColor='#f8f9fa'" 
                             onmouseout="this.style.backgroundColor='transparent'">
                            <i class="fas fa-history me-2 text-info"></i>${search}
                        </div>
                    `;
                });
                
                this.suggestionsContainer.innerHTML = html;
                this.suggestionsContainer.classList.remove('d-none');
                
                // Verify DOM update for recent searches
                const renderedItems = this.suggestionsContainer.querySelectorAll('.dashboard-suggestion-item');
                console.log('DOM updated with', renderedItems.length, 'recent search items');
                console.log('Event delegation active for recent search items');
            } else {
                this.hideSuggestions();
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
                this.hideSuggestions();
        }
    }
    
    hideSuggestions() {
        try {
            if (this.suggestionsContainer) {
                this.suggestionsContainer.classList.add('d-none');
                this.suggestionsContainer.innerHTML = '';
                console.log('Dashboard suggestions hidden');
            } else {
                console.warn('Cannot hide suggestions: container not found');
            }
        } catch (error) {
            console.error('Error hiding suggestions:', error);
        }
    }
}

// Utility functions
window.LegalFileManager = {
    formatRelativeTime: function(timestamp) {
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffInSeconds = Math.floor((now - date) / 1000);
            
            if (diffInSeconds < 60) return 'Just now';
            if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
            if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
            if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
            return date.toLocaleDateString();
        } catch (error) {
            console.error('Error formatting relative time:', error);
            return timestamp;
        }
    }
};

// Debug: Confirm LegalFileManager is loaded
console.log('LegalFileManager loaded:', !!window.LegalFileManager);

// Date filter functions
function toggleDateFilters() {
    const dateFilters = document.getElementById('date-filters');
    const datePresets = document.getElementById('date-presets');
    const toggleIcon = document.getElementById('date-toggle-icon');
    
    if (dateFilters.classList.contains('d-none')) {
        dateFilters.classList.remove('d-none');
        datePresets.classList.remove('d-none');
        toggleIcon.classList.replace('fa-chevron-down', 'fa-chevron-up');
    } else {
        dateFilters.classList.add('d-none');
        datePresets.classList.add('d-none');
        toggleIcon.classList.replace('fa-chevron-up', 'fa-chevron-down');
    }
}

function setDatePreset(preset) {
    const today = new Date();
    let startDate, endDate = today;
    
    switch(preset) {
        case 'today':
            startDate = today;
            break;
        case 'week':
            startDate = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
            break;
        case 'month':
            startDate = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
            break;
        case 'quarter':
            startDate = new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000);
            break;
        case 'year':
            startDate = new Date(today.getTime() - 365 * 24 * 60 * 60 * 1000);
            break;
    }
    
    if (startDate) {
        document.getElementById('accessed_from').value = startDate.toISOString().split('T')[0];
        document.getElementById('accessed_to').value = endDate.toISOString().split('T')[0];
        
        // Trigger search
        if (window.interactiveSearch) {
            window.interactiveSearch.performSearch();
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search functionality based on page
    if (document.getElementById('search-form')) {
        window.interactiveSearch = new InteractiveSearch();
    }
    
    if (document.getElementById('dashboard-search')) {
        window.dashboardSearch = new DashboardSearch();
    }
});
