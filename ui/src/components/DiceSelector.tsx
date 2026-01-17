import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
} from "@mui/material";
import "./DiceSelector.scss";

type DiceSelectorProps = {
  open: boolean;
  onClose: () => void;
  onSelect: (diceValue: [number, number] | null) => void;
};

// Generate all possible dice combinations
const generateDiceOptions = (): Array<{ sum: number; dice: [number, number] }> => {
  const options: Array<{ sum: number; dice: [number, number] }> = [];
  for (let die1 = 1; die1 <= 6; die1++) {
    for (let die2 = 1; die2 <= 6; die2++) {
      options.push({ sum: die1 + die2, dice: [die1, die2] });
    }
  }
  // Group by sum and return unique sums with their first dice combination
  const sumMap = new Map<number, [number, number]>();
  options.forEach(({ sum, dice }) => {
    if (!sumMap.has(sum)) {
      sumMap.set(sum, dice);
    }
  });
  return Array.from(sumMap.entries())
    .map(([sum, dice]) => ({ sum, dice }))
    .sort((a, b) => a.sum - b.sum);
};

const DiceSelector = ({ open, onClose, onSelect }: DiceSelectorProps) => {
  const diceOptions = React.useMemo(() => generateDiceOptions(), []);

  const handleRandomRoll = () => {
    onSelect(null); // null means random roll
    onClose();
  };

  const handleSelectDice = (dice: [number, number]) => {
    onSelect(dice);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      className="dice-selector"
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Choose Dice Roll</DialogTitle>
      <DialogContent>
        <div className="dice-grid">
          <Button
            variant="contained"
            color="primary"
            className="random-roll-button"
            onClick={handleRandomRoll}
            fullWidth
          >
            <Typography variant="h6">🎲 Random Roll</Typography>
          </Button>
          <div className="dice-options">
            {diceOptions.map(({ sum, dice }) => (
              <Button
                key={sum}
                variant="outlined"
                className="dice-button"
                onClick={() => handleSelectDice(dice)}
              >
                <Typography variant="body1">
                  {dice[0]} + {dice[1]} = {sum}
                </Typography>
              </Button>
            ))}
          </div>
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} className="cancel-button">
          Cancel
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DiceSelector;
