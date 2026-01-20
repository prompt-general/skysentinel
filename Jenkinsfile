pipeline {
    agent any
    
    environment {
        SKYSENTINEL_API_URL = 'https://api.skysentinel.example.com'
        SKYSENTINEL_API_KEY = credentials('skysentinel-api-key')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Terraform Init & Plan') {
            steps {
                sh '''
                    terraform init
                    terraform plan -out=tfplan
                    terraform show -json tfplan > tfplan.json
                '''
            }
        }
        
        stage('SkySentinel Policy Check') {
            steps {
                script {
                    // Install SkySentinel CLI
                    sh 'pip install skysentinel-cli'
                    
                    // Run evaluation
                    def result = sh(
                        script: '''
                            skysentinel evaluate \
                                --api-url "$SKYSENTINEL_API_URL" \
                                --api-key "$SKYSENTINEL_API_KEY" \
                                --iac-type terraform \
                                --file tfplan.json \
                                --output json
                        ''',
                        returnStdout: true
                    )
                    
                    // Parse result
                    def jsonResult = readJSON text: result
                    def status = jsonResult.result
                    def violations = jsonResult.policy_evaluation.total_violations
                    
                    // Create report
                    writeJSON file: 'skysentinel-report.json', json: jsonResult
                    
                    // Post to PR/MR if available
                    if (env.CHANGE_ID) {
                        def comment = """
                            ## SkySentinel Policy Evaluation
                            **Status:** ${status}
                            **Violations:** ${violations}
                            
                            [View Full Report](${env.BUILD_URL}/artifact/skysentinel-report.json)
                        """
                        
                        // GitHub/GitLab PR comment logic here
                        // This would use appropriate Jenkins plugins
                    }
                    
                    // Fail pipeline if blocked
                    if (status == 'block') {
                        error("SkySentinel policy evaluation blocked deployment")
                    }
                }
            }
        }
        
        stage('Deploy') {
            when {
                expression {
                    // Only deploy if SkySentinel passed
                    fileExists('skysentinel-report.json')
                }
            }
            steps {
                echo 'Deploying infrastructure...'
                // Add deployment steps here
            }
        }
    }
    
    post {
        always {
            // Archive reports
            archiveArtifacts artifacts: 'skysentinel-report.json', allowEmptyArchive: true
        }
    }
}
