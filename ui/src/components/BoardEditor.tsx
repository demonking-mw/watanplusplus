import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Grid,
  TextField,
} from "@mui/material";
import type { BoardConfig } from "../utils/apiClient";

type BoardEditorProps = {
  open: boolean;
  onClose: () => void;
  onSave: (config: BoardConfig) => void;
};

// Standard Catan board configuration
const DEFAULT_NUMBERS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12];
const DEFAULT_TILE_RESOURCES = [
  "WOOD", "WOOD", "WOOD", "WOOD",
  "BRICK", "BRICK", "BRICK",
  "SHEEP", "SHEEP", "SHEEP", "SHEEP",
  "WHEAT", "WHEAT", "WHEAT", "WHEAT",
  "ORE", "ORE", "ORE",
  null, // Desert
];
const DEFAULT_PORT_RESOURCES = [
  "WOOD", "BRICK", "SHEEP", "WHEAT", "ORE", // 2:1 ports
  null, null, null, null, // 3:1 ports
];

const RESOURCES = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"];
const NUMBERS = [2, 3, 4, 5, 6, 8, 9, 10, 11, 12];

export default function BoardEditor({
  open,
  onClose,
  onSave,
}: BoardEditorProps) {
  const [numbers, setNumbers] = useState<number[]>(DEFAULT_NUMBERS);
  const [tileResources, setTileResources] = useState<(string | null)[]>(DEFAULT_TILE_RESOURCES);
  const [portResources, setPortResources] = useState<(string | null)[]>(DEFAULT_PORT_RESOURCES);

  useEffect(() => {
    if (open) {
      // Reset to defaults when dialog opens
      setNumbers([...DEFAULT_NUMBERS]);
      setTileResources([...DEFAULT_TILE_RESOURCES]);
      setPortResources([...DEFAULT_PORT_RESOURCES]);
    }
  }, [open]);

  const handleNumberChange = (index: number, value: string) => {
    const numValue = value === "" ? 0 : parseInt(value, 10);
    if (isNaN(numValue)) return;
    
    const newNumbers = [...numbers];
    newNumbers[index] = numValue;
    setNumbers(newNumbers);
  };

  const handleTileResourceChange = (index: number, value: string) => {
    const newResources = [...tileResources];
    newResources[index] = value === "DESERT" ? null : value;
    setTileResources(newResources);
  };

  const handlePortResourceChange = (index: number, value: string) => {
    const newPorts = [...portResources];
    newPorts[index] = value === "3:1" ? null : value;
    setPortResources(newPorts);
  };

  const handleSave = () => {
    // Filter out zero/invalid numbers and ensure we have exactly 18 numbers
    const validNumbers = numbers.filter(n => n >= 2 && n <= 12);
    if (validNumbers.length !== 18) {
      alert("Please provide exactly 18 valid numbers (2-12)");
      return;
    }
    
    onSave({
      numbers: validNumbers,
      tile_resources: tileResources,
      port_resources: portResources,
    });
  };

  const handleRandomize = () => {
    // Shuffle numbers
    const shuffledNumbers = [...DEFAULT_NUMBERS].sort(() => Math.random() - 0.5);
    setNumbers(shuffledNumbers);
    
    // Shuffle tile resources
    const shuffledTiles = [...DEFAULT_TILE_RESOURCES].sort(() => Math.random() - 0.5);
    setTileResources(shuffledTiles);
    
    // Shuffle port resources
    const shuffledPorts = [...DEFAULT_PORT_RESOURCES].sort(() => Math.random() - 0.5);
    setPortResources(shuffledPorts);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        style: { maxHeight: "90vh" }
      }}
    >
      <DialogTitle>
        Custom Board Editor
        <Button
          variant="outlined"
          size="small"
          onClick={handleRandomize}
          style={{ marginLeft: "16px" }}
        >
          Randomize
        </Button>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Tile Resources (19 tiles)
          </Typography>
          <Grid container spacing={2}>
            {tileResources.map((resource, index) => (
              <Grid item xs={6} sm={4} md={3} key={index}>
                <FormControl fullWidth size="small">
                  <InputLabel>Tile {index + 1}</InputLabel>
                  <Select
                    value={resource || "DESERT"}
                    onChange={(e) => handleTileResourceChange(index, e.target.value)}
                    label={`Tile ${index + 1}`}
                  >
                    {RESOURCES.map((res) => (
                      <MenuItem key={res} value={res}>
                        {res}
                      </MenuItem>
                    ))}
                    <MenuItem value="DESERT">Desert</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            ))}
          </Grid>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Numbers (18 numbers for resource tiles)
          </Typography>
          <Grid container spacing={2}>
            {numbers.map((number, index) => (
              <Grid item xs={6} sm={4} md={3} key={index}>
                <TextField
                  fullWidth
                  size="small"
                  type="number"
                  label={`Number ${index + 1}`}
                  value={number}
                  onChange={(e) => handleNumberChange(index, e.target.value)}
                  inputProps={{ min: 2, max: 12 }}
                />
              </Grid>
            ))}
          </Grid>
        </Box>

        <Box>
          <Typography variant="h6" gutterBottom>
            Ports (9 ports: 5 specific + 4 generic 3:1)
          </Typography>
          <Grid container spacing={2}>
            {portResources.map((resource, index) => (
              <Grid item xs={6} sm={4} md={3} key={index}>
                <FormControl fullWidth size="small">
                  <InputLabel>Port {index + 1}</InputLabel>
                  <Select
                    value={resource || "3:1"}
                    onChange={(e) => handlePortResourceChange(index, e.target.value)}
                    label={`Port ${index + 1}`}
                  >
                    {RESOURCES.map((res) => (
                      <MenuItem key={res} value={res}>
                        {res} (2:1)
                      </MenuItem>
                    ))}
                    <MenuItem value="3:1">3:1 Generic</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            ))}
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          Save Board
        </Button>
      </DialogActions>
    </Dialog>
  );
}
