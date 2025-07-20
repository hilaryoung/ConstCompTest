function nextRound() {
  // Capture current round constraints data
  const constraints = [...document.querySelectorAll(".constraint-item")];
  const roundData = [];

  constraints.forEach((item, index) => {
    const meterDiv = item.querySelector(".meter");
    const meterStatus = meterDiv.className.replace("meter ", "");

    const constraintNameDiv = item.querySelector(".constraint-name");
    const constraintName = constraintNameDiv.textContent;
    const systemTag = constraintNameDiv.classList.contains("system-tagged");

    // Find margin div (the div whose class includes 'margin-')
    const marginDiv = item.querySelector("[class*='margin-']");
    const marginStatus = marginDiv.classList[1]; // second class is status like danger, warning, normal
    const marginValue = marginDiv.querySelector("div[class$='-value']").textContent;

    // Find ttb div (the div whose class includes 'ttb-')
    const ttbDiv = item.querySelector("[class*='ttb-']");
    const ttbStatus = ttbDiv.classList[1]; // status class
    const ttbValue = ttbDiv.querySelector("div[class$='-value']").textContent;

    roundData.push({
      order: index + 1,
      constraintName,
      systemTag,
      meterStatus,
      marginStatus,
      marginValue,
      ttbStatus,
      ttbValue
    });
  });

  allRoundsData.push({
    round: currentRound,
    setName: getSetName(currentRound),
    constraints: roundData
  });

  if (currentRound < totalRounds) {
    currentRound++;
    roundDisplay.textContent = currentRound;
    loadConstraints(currentRound);
  } else {
    // Send results to Flask backend then redirect to results page
    fetch('/save_results', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(allRoundsData),
    })
    .then(response => {
      if (response.ok) {
        window.location.href = '/results';
      } else {
        alert('Failed to save results.');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred while saving results.');
    });
  }
}
