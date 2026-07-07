// Projekt-Dashboard – CI/CD-Pipeline
//
// Vier separate Pipeline-Jobs (kein Multibranch), je einer pro Branch/Stufe:
// "Dashboard dev/test/int/main". Jeder Job checkt seinen Branch aus; die
// when{}-Bedingungen matchen den JOB_NAME (z. B. "Dashboard dev" enthaelt 'dev')
// und feuern die passende Deploy-Stufe:
//
//   dev  → Tests + Deploy dev   (dev.dashboard-projekte.ch   → Port 8023)
//   test → Tests + Deploy test  (test.dashboard-projekte.ch  → Port 8021)
//   int  → Tests + Deploy int   (int.dashboard-projekte.ch   → Port 8022)
//   main → Tests + Deploy prod  (dashboard-projekte.ch       → Port 8020)
//
// Promotion streng sequenziell: dev → test → int → main. Nie Stufen ueberspringen.
//
// Voraussetzungen Jenkins:
//   - SSH-Credential 'dashboard-deploy' (privater Key fuer u7031y_kaspar@83.228.238.194,
//     derselbe Key wie 'hermespia-deploy' – gleicher Infomaniak-Host)
//   - Docker + Docker-Pipeline-Plugin (fuer die Regressionstests)
//
// Voraussetzungen Server (einmalig pro Umgebung, siehe docs/DEPLOYMENT.md):
//   - Subdomain-Web-Root mit proxy.php (richtiger Port) + .htaccess
//   - .env im jeweiligen App-Verzeichnis (Secrets, DATABASE_URL)

def deploy(String subdir, String branch, String port, String workers) {
    sshagent(credentials: ['dashboard-deploy']) {
        sh """
            ssh -o StrictHostKeyChecking=no ${DEPLOY_HOST} '
                set -e
                APP=\$HOME/${subdir}
                if [ ! -d "\$APP/.git" ]; then git clone ${REPO_URL} "\$APP"; fi
                cd "\$APP"
                git remote set-url origin ${REPO_URL}
                git fetch origin
                git reset --hard origin/${branch}
                [ -d .venv ] || python3 -m venv .venv
                . .venv/bin/activate
                pip install -r requirements.txt -q
                mkdir -p data logs tmp
                PID=\$APP/tmp/gunicorn.pid
                [ -f "\$PID" ] && kill \$(cat "\$PID") 2>/dev/null || true
                sleep 1
                set -a; [ -f .env ] && . .env; set +a
                nohup gunicorn run:app \\
                    --bind 127.0.0.1:${port} --workers ${workers} --timeout 120 \\
                    --access-logfile logs/access.log \\
                    --error-logfile logs/error.log > /dev/null 2>&1 &
                echo \$! > "\$PID"
                sleep 2 && curl -sf http://127.0.0.1:${port}/healthz > /dev/null && echo "OK: ${subdir} laeuft auf ${port}"
            '
        """
    }
}

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        DEPLOY_HOST = 'u7031y_kaspar@83.228.238.194'
        REPO_URL    = 'https://github.com/kaspAir/Dashboard_Projekte'
    }

    stages {

        stage('Regressionstests') {
            steps {
                script {
                    docker.image('python:3.12-slim').inside('-u root') {
                        sh '''
                            python --version
                            pip install --no-cache-dir -r requirements.txt -r tests/requirements.txt
                            pytest -v --junitxml=reports/junit.xml
                        '''
                    }
                }
            }
            post {
                always {
                    junit 'reports/junit.xml'
                }
            }
        }

        stage('Deploy dev') {
            when { expression { env.JOB_NAME.contains('dev') } }
            steps {
                script { deploy('dashboard-dev', 'dev', '8023', '1') }
            }
        }

        stage('Deploy test') {
            when { expression { env.JOB_NAME.contains('test') } }
            steps {
                script { deploy('dashboard-test', 'test', '8021', '1') }
            }
        }

        stage('Deploy int') {
            when { expression { env.JOB_NAME.contains('int') } }
            steps {
                script { deploy('dashboard-int', 'int', '8022', '1') }
            }
        }

        stage('Deploy prod') {
            when { expression { env.JOB_NAME.contains('main') } }
            steps {
                script { deploy('dashboard', 'main', '8020', '2') }
            }
        }
    }

    post {
        success { echo 'Pipeline gruen.' }
        failure { echo 'Pipeline rot – siehe Stage-Logs und Testbericht.' }
    }
}
