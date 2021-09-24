function createBestPie(profitable_coins, profits_ordered, profitable_colour_order) {
    const profitData = {
    labels: profitable_coins,
    datasets: [{
        label: 'Trade Summary',
        data: profits_ordered,
        backgroundColor: profitable_colour_order,
        hoverOffset: 4
        }]
    };
    const profitConfig = {
        type: 'pie',
        data: profitData,
        options: { maintainAspectRatio: false }
    };
    var bestPie = new Chart(
        document.getElementById('bestPie'),
        profitConfig
    );
}

function createWorstPie(loss_coins, losses_ordered, loss_colour_order) {
    const lossData = {
        labels: loss_coins,
    datasets: [{
        label: 'Trade Summary',
        data: losses_ordered,
        backgroundColor: loss_colour_order,
        hoverOffset: 4
        }]
    };
    const lossConfig = {
        type: 'pie',
        data: lossData,
        options: { maintainAspectRatio: false }
    };
    var worstPie = new Chart(
        document.getElementById('worstPie'),
        lossConfig
    );

}
