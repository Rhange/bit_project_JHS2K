import React from 'react';
import { TouchableOpacity } from 'react-native';
import { Entypo } from '@expo/vector-icons';

const Share = ({ onPress }) => (
  <TouchableOpacity onPress={onPress}>
    <Entypo name="share" color="black" size={40} />
  </TouchableOpacity>
);

export default Share;
