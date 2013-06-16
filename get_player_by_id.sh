WD=$(dirname $0)
WD=$(cd $WD;pwd)
PLAYER=${1:?"player id"}
PLAYER_NAME=${2:?"player name"}
TEAM=${3:?"team name"}

wget "http://stats.espncricinfo.com/ci/engine/player/${PLAYER}.html?class=2;template=results;type=batting;view=innings" -O player_${PLAYER}.html

python ${WD}/player_import.py player_${PLAYER}.html "${TEAM}" "${PLAYER_NAME}" 
