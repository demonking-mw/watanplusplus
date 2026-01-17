import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  TextField,
  Box,
  Grid,
} from "@mui/material";
import type { DevelopmentCard } from "../utils/api.types";
import "./DevelopmentCardDialog.scss";

const DEVELOPMENT_CARDS: DevelopmentCard[] = [
  "KNIGHT",
  "MONOPOLY",
  "YEAR_OF_PLENTY",
  "ROAD_BUILDING",
];

type DevelopmentCardDialogProps = {
  open: boolean;
  onClose: () => void;
  onSelect: (cardType: DevelopmentCard | null, quantity: number) => void;
};

const DevelopmentCardDialog = ({
  open,
  onClose,
  onSelect,
}: DevelopmentCardDialogProps) => {
  const [selectedCard, setSelectedCard] = useState<DevelopmentCard | null>(null);
  const [quantity, setQuantity] = useState<number>(1);

  const handleRandomCard = () => {
    onSelect(null, quantity); // null means random card
    handleClose();
  };

  const handleSelectCard = (cardType: DevelopmentCard) => {
    setSelectedCard(cardType);
  };

  const handleBuy = () => {
    if (selectedCard) {
      onSelect(selectedCard, quantity);
      handleClose();
    }
  };

  const handleClose = () => {
    setSelectedCard(null);
    setQuantity(1);
    onClose();
  };

  const handleQuantityChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(event.target.value, 10);
    if (!isNaN(value) && value > 0) {
      setQuantity(value);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      className="development-card-dialog"
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Buy Development Card</DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Quantity:
          </Typography>
          <TextField
            type="number"
            value={quantity}
            onChange={handleQuantityChange}
            inputProps={{ min: 1, max: 100 }}
            size="small"
            fullWidth
          />
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Card Type:
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Button
                variant={selectedCard === null ? "contained" : "outlined"}
                color="primary"
                className="random-card-button"
                onClick={handleRandomCard}
                fullWidth
                sx={{ mb: 2 }}
              >
                <Typography variant="body1">🎲 Random Card</Typography>
              </Button>
            </Grid>
            {DEVELOPMENT_CARDS.map((card) => (
              <Grid item xs={6} key={card}>
                <Button
                  variant={selectedCard === card ? "contained" : "outlined"}
                  color={selectedCard === card ? "primary" : "inherit"}
                  onClick={() => handleSelectCard(card)}
                  fullWidth
                >
                  <Typography variant="body2">{card.replace(/_/g, " ")}</Typography>
                </Button>
              </Grid>
            ))}
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          onClick={handleBuy}
          variant="contained"
          color="primary"
          disabled={!selectedCard}
        >
          Buy {quantity} {selectedCard ? selectedCard.replace(/_/g, " ") : "Card"}
          {quantity > 1 ? "s" : ""}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DevelopmentCardDialog;
