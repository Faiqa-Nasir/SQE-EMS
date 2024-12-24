pipeline {
    agent any
    stages {
        stage('Checkout Code') {
            steps {
                // Pull the latest code from your repository
                git branch: 'main', url: 'https://github.com/Faiqa-Nasir/SQE-EMS'
            }
        }
        stage('Install Dependencies') {
            steps {
                // Install Python dependencies
                sh 'pip install -r requirements.txt'
            }
        }
        stage('Run Tests') {
            steps {
                // Run tests
                sh 'pytest -v tests/'
            }
        }
    }
    post {
        always {
            echo 'Pipeline Completed'
        }
    }
}
