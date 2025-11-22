# LSTM Model Architecture for Time Series Prediction
import torch
import torch.nn as nn
from typing import Tuple, Optional
import numpy as np


class LSTMTradingModel(nn.Module):
    """
    Bidirectional LSTM with Attention for trading signal prediction
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = True,
        use_attention: bool = True
    ):
        """
        Initialize LSTM model
        
        Args:
            input_size: Number of input features
            hidden_size: LSTM hidden layer size
            num_layers: Number of LSTM layers
            dropout: Dropout probability
            bidirectional: Use bidirectional LSTM
            use_attention: Use attention mechanism
        """
        super(LSTMTradingModel, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.use_attention = use_attention
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional,
            batch_first=True
        )
        
        # Direction multiplier
        direction_multiplier = 2 if bidirectional else 1
        lstm_output_size = hidden_size * direction_multiplier
        
        # Attention layer
        if use_attention:
            self.attention = nn.Sequential(
                nn.Linear(lstm_output_size, hidden_size),
                nn.Tanh(),
                nn.Linear(hidden_size, 1)
            )
        
        # Fully connected layers
        self.fc = nn.Sequential(
            nn.Linear(lstm_output_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Sigmoid()  # Output probability [0, 1]
        )
    
    def forward(
        self,
        x: torch.Tensor,
        hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size)
            hidden: Optional initial hidden state
            
        Returns:
            Output tensor of shape (batch_size, 1) with prediction probabilities
        """
        # LSTM forward
        lstm_out, (hidden, cell) = self.lstm(x, hidden)
        # lstm_out shape: (batch_size, seq_len, hidden_size * num_directions)
        
        # Apply attention if enabled
        if self.use_attention:
            # Calculate attention weights
            attention_weights = self.attention(lstm_out)  # (batch_size, seq_len, 1)
            attention_weights = torch.softmax(attention_weights, dim=1)
            
            # Apply attention weights
            context = torch.sum(attention_weights * lstm_out, dim=1)  # (batch_size, hidden_size * num_directions)
        else:
            # Use last output
            context = lstm_out[:, -1, :]
        
        # Fully connected layers
        output = self.fc(context)
        
        return output
    
    def predict_proba(self, x: torch.Tensor) -> np.ndarray:
        """
        Predict probabilities (for sklearn-style interface)
        
        Args:
            x: Input tensor
            
        Returns:
            NumPy array of probabilities
        """
        self.eval()
        with torch.no_grad():
            preds = self.forward(x)
        return preds.cpu().numpy()


class LSTMTrainer:
    """Trainer for LSTM model"""
    
    def __init__(
        self,
        model: LSTMTradingModel,
        learning_rate: float = 0.001,
        device: str = 'cpu'
    ):
        self.model = model.to(device)
        self.device = device
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        self.criterion = nn.BCELoss()  # Binary cross-entropy for classification
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': []
        }
    
    def train_epoch(
        self,
        train_loader: torch.utils.data.DataLoader
    ) -> Tuple[float, float]:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(self.device)
            batch_y = batch_y.to(self.device)
            
            # Forward pass
            outputs = self.model(batch_x)
            loss = self.criterion(outputs, batch_y)
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            # Metrics
            total_loss += loss.item()
            predictions = (outputs > 0.5).float()
            correct += (predictions == batch_y).sum().item()
            total += batch_y.size(0)
        
        avg_loss = total_loss / len(train_loader)
        accuracy = correct / total
        
        return avg_loss, accuracy
    
    def validate(
        self,
        val_loader: torch.utils.data.DataLoader
    ) -> Tuple[float, float]:
        """Validate model"""
        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                outputs = self.model(batch_x)
                loss = self.criterion(outputs, batch_y)
                
                total_loss += loss.item()
                predictions = (outputs > 0.5).float()
                correct += (predictions == batch_y).sum().item()
                total += batch_y.size(0)
        
        avg_loss = total_loss / len(val_loader)
        accuracy = correct / total
        
        return avg_loss, accuracy
    
    def fit(
        self,
        train_loader: torch.utils.data.DataLoader,
        val_loader: torch.utils.data.DataLoader,
        epochs: int = 50,
        early_stopping_patience: int = 10
    ):
        """Train model with early stopping"""
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(epochs):
            train_loss, train_acc = self.train_epoch(train_loader)
            val_loss, val_acc = self.validate(val_loader)
            
            # Save history
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_acc'].append(val_acc)
            
            print(f"Epoch {epoch+1}/{epochs} - "
                  f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f} - "
                  f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                torch.save(self.model.state_dict(), 'best_lstm_model.pth')
            else:
                patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    print(f"Early stopping at epoch {epoch+1}")
                    break
        
        # Load best model
        self.model.load_state_dict(torch.load('best_lstm_model.pth'))
