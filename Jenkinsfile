def notifyStatus(String stageName, String status, String details = "") {
    def subject = "${status}: Jenkins Pipeline - ${env.JOB_NAME} [${env.BUILD_NUMBER}] - ${stageName}"
    def body = "Stage '${stageName}' ${status}.\n\nDetails:\n${details}\n\nCheck console output at: ${env.BUILD_URL}console"
    
    // IMPORTANT: You must configure an SMTP server in Jenkins (Manage Jenkins -> System -> E-mail Notification) for this to work.
    // Replace the 'to' email address with your actual email.
    mail to: 'your-email@example.com', 
         subject: subject,
         body: body
}

pipeline {
    agent none

    environment {
        DOCKER_IMAGE = 'armingrobbelaar/investment_app'
        DOCKER_TAG = 'latest'
        DOCKER_CREDS = 'dockerhub-credentials'
        GITHUB_USER = 'Armin-Grobbelaar'
        GITHUB_REPO = 'Investment-Management'
        // Please add a Secret Text credential in Jenkins with ID 'github-pat' containing your GitHub token.
        // It will be used to automatically push code to GitHub.
    }

    stages {
        stage('Checkout & Setup') {
            agent { label 'built-in' }
            steps {
                checkout scm
                script {
                    notifyStatus('Checkout & Setup', 'SUCCESS', 'Repository successfully cloned.')
                }
            }
            post {
                failure {
                    script {
                        notifyStatus('Checkout & Setup', 'FAILED', 'Failed to clone repository.')
                    }
                }
            }
        }

        stage('Run Tests') {
            agent { label 'jenkins-agent' }
            steps {
                script {
                    try {
                        sh '''
                        # Inside the jenkins-agent docker container
                        # Install dependencies for backend testing
                        apt-get update && apt-get install -y python3-pip python3-venv curl
                        
                        # Setup Node.js for frontend testing
                        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
                        apt-get install -y nodejs

                        python3 -m venv venv
                        . venv/bin/activate
                        pip install -r investment_backend/requirements.txt
                        pip install pytest httpx
                        
                        # Run backend tests
                        cd investment_backend
                        PYTHONPATH=. pytest tests/ -v
                        cd ..

                        # Run frontend tests
                        cd investment_frontend
                        npm install --legacy-peer-deps
                        npm test
                        '''
                        notifyStatus('Run Tests', 'SUCCESS', 'All tests passed successfully.')
                    } catch (Exception e) {
                        notifyStatus('Run Tests', 'FAILED', "Tests failed: ${e.getMessage()}")
                        error("Tests failed")
                    }
                }
            }
        }

        stage('Push Code to GitHub') {
            agent { label 'built-in' }
            steps {
                script {
                    try {
                        withCredentials([string(credentialsId: 'github-pat', variable: 'GITHUB_TOKEN')]) {
                            sh """
                            git config --global user.email "jenkins@example.com"
                            git config --global user.name "Jenkins CI"
                            
                            git remote set-url origin https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git
                            
                            # Push changes
                            git push origin HEAD:main
                            """
                        }
                        notifyStatus('Push Code to GitHub', 'SUCCESS', 'Code pushed to GitHub successfully.')
                    } catch (Exception e) {
                        echo "GitHub push failed or already up-to-date: ${e.getMessage()}"
                        notifyStatus('Push Code to GitHub', 'WARNING/FAILED', "Push step encountered an issue (might be up to date): ${e.getMessage()}")
                    }
                }
            }
        }

        stage('Build & Push Docker Image') {
            agent { label 'built-in' }
            steps {
                script {
                    try {
                        echo "Building image ${DOCKER_IMAGE}:${DOCKER_TAG}..."
                        sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
                        
                        docker.withRegistry('https://index.docker.io/v1/', DOCKER_CREDS) {
                            echo "Pushing image ${DOCKER_IMAGE}:${DOCKER_TAG} to DockerHub..."
                            sh "docker push ${DOCKER_IMAGE}:${DOCKER_TAG}"
                        }
                        notifyStatus('Build & Push Docker Image', 'SUCCESS', 'Docker image built and pushed to DockerHub.')
                    } catch (Exception e) {
                        notifyStatus('Build & Push Docker Image', 'FAILED', "Docker build/push failed: ${e.getMessage()}")
                        error("Docker build/push failed")
                    }
                }
            }
        }

        stage('Redeploy Local Instance') {
            agent { label 'built-in' }
            steps {
                script {
                    try {
                        echo "Deploying local instance..."
                        sh """
                        docker pull ${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker stop investment_app || true
                        docker rm investment_app || true
                        docker run -d --name investment_app --network host --restart unless-stopped \\
                            -e POSTGRES_HOST=localhost -e POSTGRES_PORT=5432 \\
                            -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=changeme \\
                            -e INVESTMENTS_DB=Investments -e USERS_DB=Users \\
                            -e NODE_ENV=production -e PORT=3000 \\
                            ${DOCKER_IMAGE}:${DOCKER_TAG}
                        """
                        notifyStatus('Redeploy Local Instance', 'SUCCESS', 'Local instance successfully updated and redeployed.')
                    } catch (Exception e) {
                        notifyStatus('Redeploy Local Instance', 'FAILED', "Redeploy failed: ${e.getMessage()}")
                        error("Redeploy failed")
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                echo 'Cleaning up intermediate images...'
                sh 'docker image prune -f || true'
            }
        }
        success {
            script {
                notifyStatus('Pipeline Finished', 'SUCCESS', 'The entire CI/CD pipeline completed successfully.')
            }
        }
        failure {
            script {
                notifyStatus('Pipeline Finished', 'FAILED', 'The CI/CD pipeline failed. Check Jenkins logs for details.')
            }
        }
    }
}
